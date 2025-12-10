# AGENTS.md  
**（OpenAI Codex CLI 用／Odoo カスタムアドオン開発ガイド）**

このリポジトリでは、**Odoo 19 Community Edition** を基盤として、  
`custom_addons/` 配下にカスタムモジュールを実装・管理します。

本ファイルは **開発者（人間）と Codex CLI の両方に向けた開発ガイド**です。

---

# 1. リポジトリの目的

- Odoo 19 のカスタム機能を `custom_addons/` 配下で開発する
- 標準 Odoo コアを改変せず、すべてを **カスタムアドオンとして実装する**
- 主な開発対象：
  - 従業員向けポータルモジュール（掲示板・タスク管理）
  - その他業務アプリ・Odoo拡張機能

---

# 2. ディレクトリ構成（重要）

本リポジトリでは、次の構成を標準とします：

```text
odoo/                      # Git リポジトリのルート
├─ custom_addons/          # カスタムモジュール置き場 ← Codex が編集する領域
│   └─ employee_portal/    # 今回のメイン対象モジュール
│       ├─ __init__.py
│       ├─ __manifest__.py
│       ├─ models/
│       ├─ views/
│       ├─ security/
│       └─ data/
├─ docker-compose.yml
├─ odoo.conf
└─ AGENTS.md               # ← このガイド

🔒 Codex への重要指示

作業対象は必ず custom_addons/ 以下に限定すること

odoo/addons/（コアモジュール）は 絶対に編集しない

カスタマイズが必要な場合は 必ずカスタムモジュールで継承する

3. 主な開発対象モジュール：employee_portal

このモジュールは以下の機能を提供する：

📌 3.1 掲示板（Board）
モデル

employee.board.category

employee.board.post

主な機能

店舗・従業員向けのお知らせ

マニュアル（HTML / 添付ファイル）

メニュー情報の掲示

公開期間・優先表示（ピン留め）

📌 3.2 タスク管理（Task）
モデル

employee.task.template（日次・週次・月次テンプレート）

employee.task（従業員ごとの実タスク）

主な要件

日次／週次／月次の定期タスク自動生成（Cron）

従業員は「マイタスク」だけ閲覧し、完了処理できる

完了タスクは一覧から非表示にする（履歴としては残す）

掲示板記事と紐付け（マニュアル参照）

4. Codex が行うべきタスク

Codex は以下を実行できる：

✔ モデルの作成・修正（Python: models/*.py）

Odoo API (models.Model, fields, @api.model, @api.depends 等) に準拠すること

例：employee_task.py, employee_board.py など

✔ ビューの作成・修正（XML: views/*.xml）

kanban, tree, form, search, action, menuitem を必要に応じて編集

Odoo のビュー構造に従うこと

✔ セキュリティ設定（security/*.xml, ir.model.access.csv）

グループ：

group_employee_portal_user

group_employee_portal_manager

レコードルール：

従業員は自分のタスクのみ閲覧・更新できる

マネージャーは自社の全タスク・掲示板を管理できる

✔ Cron の作成（data/*.xml）

ir.cron により日次でタスクを自動生成

既存タスクの重複作成を防ぐ

✔ リファクタリング・最適化

モジュールのコード品質向上

Odoo ベストプラクティスに従うよう改善

5. 変更ポリシー
5.1 コアコード改変禁止

/odoo/addons/ 以下の Odoo 標準モジュールは一切編集しない

必要があれば 継承（_inherit）で拡張する

5.2 custom_addons のみ編集可能

本リポジトリの変更は必ず custom_addons/ 配下で完結させること

特にこのプロジェクトでは custom_addons/employee_portal/ が主対象

6. Codex 実行時の前提

Codex CLI（codex コマンド）を使う場合：

作業ディレクトリ

Codex を実行する際のカレントディレクトリは、原則として：

odoo/custom_addons/employee_portal/


とする。
こうすることで、Codex がこのモジュール内だけを編集しやすくなる。

Codex が生成するファイル例

Python モデルファイル
models/employee_task.py

XML ビューファイル
views/employee_task_views.xml

セキュリティ設定
security/employee_portal_security.xml, security/ir.model.access.csv

Cron 設定
data/employee_task_cron.xml

7. コードの品質基準

Odoo の標準 API を尊重する

Python は PEP8 + Odoo コーディングスタイル準拠

クラス名：CamelCase

フィールド名：snake_case

XML は Odoo 標準ビュー構造に従う

不要な書き換えや破壊的変更は避ける

コメントでは「何を」「なぜ」実装しているかを明記する

8. 開発ワークフロー（人間 & Codex 共通）

Codex に作業を依頼（例：モデル追加、ビュー修正など）

Codex が生成した差分を確認

ローカル Docker で Odoo を再起動（-u employee_portal などでモジュール更新）

画面から動作を確認

問題なければ Git にコミット

9. Codex への絶対命令（まとめ）

Codex は、custom_addons/ 以外のディレクトリを変更しないこと。
Odoo 本体のコードには触れず、すべてを employee_portal の中で完結させること。

10. 参考情報：employee_portal の役割

掲示板（マニュアル・メニュー・告知）

従業員タスク（日次／週次／月次）

掲示板記事とタスクを紐付けて、タスクからマニュアルにジャンプできるようにする

11. Codex 用「最初の初期指示セット」（コピペ用）

Codex に最初にタスクを与えるときは、以下を丸ごと貼ってください：

このリポジトリは Odoo 19 CE 用です。
カスタムモジュールは custom_addons/employee_portal/ にあります。
編集対象は必ず custom_addons/employee_portal/ 以下に限定してください。
Odoo 本体（odoo/addons 等）は一切編集しないでください。

employee_portal モジュールの目的は、従業員向けの掲示板（マニュアル・メニュー・社内告知）と、日次／週次／月次の定期タスク管理機能を提供することです。

あなたの役割は次のとおりです：

既存コードを読み、Odoo のベストプラクティスに沿ってモデル・ビュー・セキュリティ・Cron を実装・改善すること。

モデルやビューの追加／変更は、models/, views/, security/, data/ の下に行うこと。

コアモジュールの改変は行わず、必要な場合は employee_portal から継承して実現すること。

これらの前提を守りつつ、指定するタスクを実行してください。

この初期文のあとに、具体的な依頼内容（プロンプト） を続けて書きます。

12. Codex で employee_portal をリファクタリングするプロンプト例

以下は、実際に Codex に投げる具体的な指示例です。

12.1 モジュール構成を作成するプロンプト例

custom_addons/employee_portal/ で、従業員ポータル用の Odoo モジュールを作成してください。
すでに __init__.py と __manifest__.py がある前提で、次を実装してください：

models/employee_board.py に、掲示板カテゴリと掲示板記事のモデルを定義すること

employee.board.category（name, sequence）

employee.board.post（name, category_id, type, body_html, company_id, publish_from, publish_to, is_pinned など）

models/employee_task.py に、タスクテンプレートと従業員タスクを定義すること

employee.task.template（frequency, weekday, month_day, employee_ids など）

employee.task（employee_id, date, status, template_id など）

views/employee_board_views.xml と views/employee_task_views.xml に、Tree / Form / Kanban / Action / Menu を定義すること。

security/employee_portal_security.xml と security/ir.model.access.csv を作成し、従業員ユーザとマネージャーの権限を設定すること。

data/employee_task_cron.xml に ir.cron を定義し、日次でタスクを生成するメソッドを呼ぶようにすること。

すべて custom_addons/employee_portal 以下にファイルを作成・更新してください。

12.2 既存コードをリファクタリングするプロンプト例

custom_addons/employee_portal/models/employee_task.py と
custom_addons/employee_portal/views/employee_task_views.xml を読み、
次の方針でリファクタリングしてください：

EmployeeTask モデルに、重複タスク作成を防ぐロジックが既にあるか確認し、なければ _generate_from_templates 内で search_count を使用して同一日付・同一テンプレート・同一従業員のタスクを作成しないように実装する。

cron_generate_tasks メソッドの中で、fields.Date.context_today を一度だけ呼び出し、変数に保持するようにして無駄な重複処理を減らす。

views/employee_task_views.xml の Kanban 表示で、ステータスに応じてラベルをわかりやすく表示する（例：未実施 / ✅ 完了 / ✖ キャンセル）。

既存のフィールド名やモデル名は変更しないこと。

出力では、変更したファイルの完全な内容をそれぞれ示してください。

12.3 セキュリティ・レコードルール調整のプロンプト例

custom_addons/employee_portal/security/employee_portal_security.xml と
security/ir.model.access.csv を確認し、次の条件を満たすように修正してください：

group_employee_portal_user は、自分に紐づく従業員 (hr.employee.user_id == res.users.id) のタスクのみ read/write できること。

group_employee_portal_manager は、自社 (company_id) のすべてのタスクと掲示板投稿を read/write/create/unlink できること。

Odoo の multi-company ルールに従い、company_ids を使ったドメインを利用すること。

修正後の XML / CSV ファイル全文を出力してください。

12.4 小さな改善タスクのプロンプト例

views/employee_board_views.xml のフォームビューに、「メッセージ」タブ（Chatter）を追加し、mail.thread の機能が使えるようにしてください。
すでに EmployeeBoardPost モデルは mail.thread を継承している前提です。
Chatter 用の <field name="message_follower_ids"/> と <field name="message_ids"/> を Notebook に追加し、既存レイアウトと整合性を保つようにしてください。
