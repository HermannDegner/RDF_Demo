# RDL Demos

RDL（関係力学言語 / Relational Dynamics Language）をベースにした実験デモ集。  
p5.js によるビジュアルシミュレーションと、CLIチャットボットで構成される。

**GitHub Pages:** https://hermannDegner.github.io/RDL_Demos/

理論ベース: [Limit-Space_Relational-Dynamics-Language](https://github.com/HermannDegner/Limit-Space_Relational-Dynamics-Language)

---

## デモ一覧（p5.js / ブラウザ）

| フォルダ | タイトル | 概要 |
|---------|---------|------|
| [demo0/](demo0/) | p5.js sketch | 温度制御シミュレーション |
| [demo1/](demo1/) | RDF v4 | 近傍セル評価移動 |
| [demo2/](demo2/) | Non-Euclidean Warp Navigation | 迷路内熱場・フロー学習 |
| [demo3/](demo3/) | RDF minimal world ver2 | 草・捕食者・被食者 |
| [demo4/](demo4/) | RDF minimal world ver2.1 | 少数戦術・視覚/音センサー |
| [demo5/](demo5/) | RDF minimal world ver3 | 水場追加・複合生存資源 |
| [demo6/](demo6/) | RDF Rabbit Demo v3.1 | アクティブ脅威・アンカー行動 |

---

## rdl_bot（CLIチャットボット）

RDL語彙でユーザーの入出力を構造化し、H蓄積 → leap → LLM学習 のサイクルで自律拡張するボット。

```bash
cd rdl_bot
pip install -r requirements.txt
py main.py
```

APIキーなしでも動作する（手動 seed 20ノード付き）。  
詳細は [rdl_bot/README.md](rdl_bot/README.md) を参照。
