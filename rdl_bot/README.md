# rdl_bot — RDL個人M_B外部化AI v0.1

RDL（関係力学言語）の語彙でユーザーの入出力を構造化し、  
H蓄積 → leap → LLM問い合わせ → ノード学習 というサイクルで自律拡張するCLIチャットボット。

---

## 起動

```bash
# 通常起動（graph.json が空なら seed_v0.1.json を自動ロード）
py main.py

# LLMで追加ノードを生成してから起動（ANTHROPIC_API_KEY 必要）
py main.py --seed
```

依存:
```bash
pip install -r requirements.txt   # anthropic>=0.40.0
```

APIキーなしでも seed_v0.1.json（手動20ノード）で最小動作する。

---

## コマンド

| コマンド | 説明 |
|---------|------|
| `/llm on\|off\|once` | LLMモード切替 |
| `/h` | H状態表示（H_pre / H_post / θ） |
| `/graph` | グラフ統計（総ノード数・source別・phase別・status別） |
| `/hot` | H値が高いノードTOP3 |
| `/quit` | グラフ保存して終了 |
| `y / n / ?` | 直前応答へのフィードバック（同意 / 否定 / 言い換え要求） |

---

## ファイル構成

```
rdl_bot/
├── main.py          CLIループ + respond() + metabolize()
├── node_graph.py    Node / NodeGraph（検索・保存・読込）
├── h_state.py       HState（H_pre/H_post・leap判定）
├── llm_bridge.py    LLMBridge（Anthropic API・ξポンプ）
├── requirements.txt
└── data/
    ├── seed_v0.1.json   手動 Phase 0 ノード（20件・APIキー不要）
    └── graph.json       実行時に生成・更新される学習グラフ
```

---

## 設計メモ

### H（フラストレーション）

- `H_pre`：入力ミス時に蓄積（軽め、weight=0.4）
- `H_post`：ユーザー反応（deny/rephrase/silence）で蓄積（重め、weight=1.0）
- `should_leap()` は `H_pre×0.4 + H_post` の合成値で判定
- 閾値 θ=2.0 を超えると leap → LLM問い合わせ or グラフ内合成

### ノードライフサイクル

```
source: manual / llm_seed / llm_learned / graph_composed
phase:  M_lat（候補）→ activation_count≥3 で M_act（安定）
status: candidate → active → quarantined / deprecated
```

- `manual` ノードは TTL=200（デフォルト）で decay しない（`confidence` 減衰のみ）
- `llm_seed` ノードは TTL<=0 で `retire_dead_nodes()` により削除（50ターンごと）
- 毎ターン `decay_confidence(rate=0.995)` が全ノードに走る

### leap フロー

```
ミス × N回 → H閾値超過 → should_leap() = True
  ├── LLM:on  → ask_for_node() → Node(source=llm_learned, phase=M_lat)
  └── LLM:off → compose_from_graph()（近傍ノードのresponseを借用）
```

### 既知の制限（Phase 1）

- 検索は部分文字列マッチ。日本語助詞誤マッチあり → 将来 sentence-transformers に切替予定
- グラフ内合成（LLM:off 時）は近傍借用のみ。W_ij による本格合成は Phase 4
- SFO・MBTI初期値・ξ pool・M_Δ本格実装は未着手

---

## フェーズロードマップ（設計図より）

| Phase | 内容 | 状態 |
|-------|------|------|
| 0 | 普遍ノード種まき（手動 or LLM） | 完了 |
| A | CLIループ・H蓄積・leap・LLM学習 | 実装中 |
| B | SFO初期値（MBTI入力）・drift | 未着手 |
| C | ξ pool・M_Δ本格代謝 | 未着手 |
| D | W_ij・ノード間合成・限界の地図UI | 未着手 |
