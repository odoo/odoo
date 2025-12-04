📄 Odoo モジュールインストール手順（custom_addons 用）

このドキュメントでは、ローカル Docker 開発環境に配置した Odoo カスタムモジュール
（例：custom_addons/module_template）を Odoo 本体にインストールする手順をまとめています。

🗂 1. モジュールの配置を確認する

docker-compose.yml の volumes: 設定で
Odoo コンテナに custom_addons がマウントされていることが前提条件です。

odoo:
  volumes:
    - ./custom_addons:/mnt/extra-addons

🔍 配置パス
C:\GitLab\odoo\odoo_dev\custom_addons\module_template\


この中に以下のファイルが存在すれば OK：

__init__.py
__manifest__.py
models/
views/
security/

🔁 2. Odoo コンテナを再起動する

Odoo はモジュールリストを 起動時に読み込む ため、再起動が必要です。

docker compose restart odoo


※ モジュールの Python ファイル・XML ファイルを追加した場合も再起動が必要。

🛠 3. Odoo をデバッグモードで開く

ブラウザで Odoo を開く：

http://localhost:8069


右上に示されるユーザー名メニューからデベロッパーモード (Developer Mode) を ON にする。

📦 4. 「アプリ一覧を更新（Update Apps List）」を実行

デバッグモードにすると、アプリ画面に
「アプリ一覧を更新（Update Apps List）」 ボタンが出ます。

操作手順：

上部メニュー「アプリ(Apps)」へ移動

右上に「アプリ一覧を更新」ボタンが表示

「アプリ一覧を更新」 → 「更新(Update)」をクリック

📌 この操作で
custom_addons 内の新モジュールが Odoo に認識される。

🔍 5. モジュールを検索する

アプリ画面で次の単語を検索してください：

Module Template Sample


または

module_template


（__manifest__.py の "name" で検索されます）

▶ 6. モジュールをインストールする

モジュールのカードをクリック

「インストール（Install）」ボタンを押す

Odoo が以下を行います：

モデルの table を PostgreSQL に作成

アクセス権（security/ir.model.access.csv）を適用

ビュー（Tree / Form / Menu）を登録

メニューを自動生成

🧭 7. メニューを確認する

インストール後、
Odoo の画面上部のメニューに新しいカテゴリが追加されます：

Sample Dev
└─ Sample Items


クリックすると、テンプレートで作成したツリービュー・フォームビューが表示されます。

🧪 8. モジュールの動作確認
✔ レコード作成（create）

画面右上の「作成 Create」ボタンを押す → 新規レコードを作成
→ Python の create() にブレークポイントがあれば VSCode が停止

✔ ボタン実行（Confirm / Done）

フォーム画面のフッターにある：

Confirm → action_confirm()

Done → action_done()

が呼ばれる。

debugpy でブレークポイントを置いていれば止まる。

🔄 9. モジュールの更新（仕様変更した場合）
Python コードを変更した場合（models/*.py）

→ Odoo コンテナを再起動

docker compose restart odoo

XML（ビュー）を変更した場合

→ 更新は Odoo 画面から可能

アプリ画面 →
対象モジュール →
「アップグレード（Upgrade）」ボタンを押す

🗑 10. モジュールのアンインストール（削除）

アプリ画面 → モジュールをクリック →
「アンインストール（Uninstall）」で削除できます。

（DB のテーブルも削除されます）

🛠 11. トラブルシューティング
❗ モジュールが一覧に出てこない

__manifest__.py に構文エラーがある

モジュールフォルダ名が間違っている

Odoo コンテナを再起動していない

Update Apps List をしていない

❗ インストール時に500エラー

__manifest__.py の depends に不足

security/ir.model.access.csv の model_id が不正

XML の <record> や <field> の typo

❗ メニューが表示されない

menuitem の parent が切れている

action の ID が間違っている

access.csv の権限が足りない

🎉 完了

最小構成の custom_addons モジュールは、
この手順どおりに進めれば 確実に Odoo にインストールできます。