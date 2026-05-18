"""
main.py
RDL個人M_B外部化AI - CLI ループ (Phase 0 + Phase A)

使い方:
  python main.py              通常起動
  python main.py --seed       Phase 0: LLMで初期ノードを種まきしてから起動

コマンド（会話中）:
  /llm on|off|once            LLMモード切替
  /h                          H状態を表示
  /graph                      グラフ統計を表示
  /hot                        H高いノードを表示
  /quit                       終了
  y / n / ?                   直前の応答へのフィードバック（y=同意 n=否定 ?=言い換え）
"""

import sys
import os

# Windows での文字化け防止
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

# カレントディレクトリを data/ の親に合わせる
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import json

from node_graph import NodeGraph, Node
from h_state import HState
from llm_bridge import LLMBridge


BANNER = """
========================================
  sumitsuku-AI  /  RDL Bot  v0.1
  Phase 0->A  CLI prototype
========================================
  /llm on|off|once  /h  /graph  /hot  /quit
  feedback: y(agree) n(deny) ?(rephrase)
"""


def apply_feedback(fb: str, last_node_id: str, h: HState) -> None:
    fb = fb.strip().lower()
    if fb == "n":
        h.on_deny(last_node_id)
        print("  → 否定を記録しました (H_post +1.0)")
    elif fb == "?":
        h.on_rephrase(last_node_id)
        print("  → 言い換えを記録しました (H_post +0.3)")
    elif fb == "y":
        h.on_agree(last_node_id)
        print("  → 同意を記録しました (H_post x0.7)")
    # 空Enterは H を上げない


def feedback_prompt(last_node_id: str, h: HState) -> None:
    """応答後のフィードバックを求める。"""
    fb = input("  [fb] > ")
    apply_feedback(fb, last_node_id, h)


def handle_command(cmd: str, llm: LLMBridge, graph: NodeGraph, h: HState) -> bool:
    """コマンド処理。Trueなら次のループへ。"""
    parts = cmd.strip().split()
    name = parts[0]

    if name == "/quit":
        graph.save()
        print("グラフを保存して終了します。")
        sys.exit(0)

    elif name == "/llm":
        if len(parts) < 2:
            print(f"  LLMモード: {llm.mode}  (利用可能: {llm.available()})")
        else:
            mode_map = {"on": "on", "off": "off", "once": "on-once"}
            m = mode_map.get(parts[1])
            if m:
                llm.set_mode(m)
                print(f"  LLMモード → {llm.mode}")
            else:
                print("  on / off / once を指定してください")

    elif name == "/h":
        print(f"  {h.summary()}")

    elif name == "/graph":
        s = graph.stats()
        print(f"  ノード総数: {s['total']}")
        print(f"  ソース別: {s['by_source']}")
        print(f"  フェーズ別: {s['by_phase']}")

    elif name == "/hot":
        hot = h.hot_nodes()
        if not hot:
            print("  H蓄積なし")
        for nid, v in hot:
            n = graph.get_by_id(nid)
            label = n.rdl_type if n else nid
            print(f"  {label} ({nid}): {v:.2f}")

    else:
        print(f"  不明なコマンド: {name}")

    return True


_turn_count = 0


def metabolize(graph: NodeGraph, retire: bool = False):
    """M_Δ相: 全ノードを減衰する。retire=True のとき死滅ノードも退場。"""
    for n in list(graph.nodes.values()):
        n.decay_confidence()
    if retire:
        graph.retire_dead_nodes()


def compose_from_graph(user_input: str, graph: NodeGraph) -> tuple[str, str]:
    """
    LLM:off 時の暫定グラフ内合成。
    最も入力長比率が高い部分一致ノードの response を借りる。
    """
    text_lower = user_input.lower()
    best_node = None
    best_score = 0.0

    for node in graph.nodes.values():
        for pattern in node.input:
            if pattern.lower() in text_lower or text_lower in pattern.lower():
                score = len(pattern) / max(len(text_lower), 1) * node.confidence
                if score > best_score:
                    best_score = score
                    best_node = node

    if best_node and best_score > 0.1:
        resp = best_node.response or f"[{best_node.rdl_type}（近傍合成）]"
        return f"{resp}（※近傍合成）", best_node.id

    return "[未知の入力です。/llm on で外部参照できます]", "__none__"


def respond(user_input: str, graph: NodeGraph, h: HState, llm: LLMBridge) -> tuple[str, str]:
    """
    応答を生成して返す。
    返り値: (response_text, last_node_id)
    """
    node, match_type, nearest = graph.search(user_input)

    if match_type == "exact":
        h.on_exact(node.id)
        node.touch()
        graph.save()
        resp = node.response or f"[{node.rdl_type}] {user_input}"
        return resp, node.id

    elif match_type == "partial":
        h.on_partial(node.id)
        node.touch()
        graph.save()
        resp = node.response or f"[{node.rdl_type}（部分一致）] {user_input}"
        return resp, node.id

    else:
        # ミス：最近傍ノードIDをコンテキストとして渡す
        context_nid = nearest.id if nearest else "__none__"
        h.on_miss(context_nid)
        leap_needed, hot_nid = h.should_leap()

        if leap_needed and llm.mode in ("on", "on-once"):
            print("  [H閾値超過 → LLMに問い合わせ中...]")
            new_node = llm.ask_for_node(user_input)
            if new_node:
                graph.add(new_node)
                graph.save()
                h.leap_done(hot_nid)
                resp = new_node.response or f"[新規学習: {new_node.rdl_type}]"
                return resp, new_node.id
            else:
                # LLM失敗 → テキスト応答にフォールバック
                raw = llm.ask(user_input)
                if raw:
                    return raw, "__llm__"

        elif leap_needed:
            print(f"  [H閾値超過 (θ={h.theta:.2f}) — グラフ内合成を試みます]")

        return compose_from_graph(user_input, graph)


def load_seed_json(graph: NodeGraph, path: str = "data/seed_v0.1.json") -> int:
    """グラフが空のとき手動 seed JSON を読み込む。追加数を返す。"""
    try:
        with open(path, encoding="utf-8") as f:
            items = json.load(f)
        for d in items:
            graph.add(Node(
                inputs=d.get("inputs", []),
                rdl_type=d.get("rdl_type", "未分類"),
                spatial_tag=d.get("spatial_tag", "概念"),
                response=d.get("response"),
                source="manual",
                confidence=0.9,
            ))
        graph.save()
        return len(items)
    except FileNotFoundError:
        return 0


def phase0_seed(graph: NodeGraph, llm: LLMBridge):
    """Phase 0: LLMで普遍ノードを種まきする。"""
    if not llm.available():
        print("  LLMが利用不可 (ANTHROPIC_API_KEY未設定) — seedをスキップします")
        return

    print("  Phase 0: LLMで初期ノードを生成中...")
    nodes = llm.seed_universal_nodes()
    for n in nodes:
        graph.add(n)
    graph.save()
    print(f"  {len(nodes)} 個の seed ノードを追加しました。")


def main():
    seed_mode = "--seed" in sys.argv

    graph = NodeGraph("data/graph.json")
    h = HState(theta=2.0)
    llm = LLMBridge()

    # LLM利用可能なら初期モードをonに
    if llm.available():
        llm.set_mode("on")

    print(BANNER)

    if seed_mode:
        phase0_seed(graph, llm)

    # グラフが空なら手動 seed を自動ロード
    if graph.stats()["total"] == 0:
        n = load_seed_json(graph)
        if n:
            print(f"  seed_v0.1.json から {n} ノードをロードしました。")

    s = graph.stats()
    print(f"  グラフ読込: {s['total']} ノード  LLM: {llm.mode} ({llm.model})")
    print()

    last_node_id = "__none__"

    while True:
        try:
            user_input = input("あなた > ").strip()
        except (EOFError, KeyboardInterrupt):
            graph.save()
            print("\n終了します。")
            break

        if not user_input:
            h.on_silence(last_node_id)
            continue

        if user_input.startswith("/"):
            handle_command(user_input, llm, graph, h)
            continue

        # フィードバックショートカット（直前応答への反応）
        if user_input in ("y", "n", "?") and last_node_id != "__none__":
            apply_feedback(user_input, last_node_id, h)
            continue

        response, last_node_id = respond(user_input, graph, h, llm)
        print(f"Bot  > {response}")

        # 毎ターン簡易フィードバック
        feedback_prompt(last_node_id, h)

        # M_Δ相: 代謝（毎ターン減衰、50ターンごとに死滅退場＋保存）
        global _turn_count
        _turn_count += 1
        retire = (_turn_count % 50 == 0)
        metabolize(graph, retire=retire)
        if retire:
            graph.save()


if __name__ == "__main__":
    main()
