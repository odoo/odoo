# Odoo 19 ローカル開発環境構築ガイド（完全版）
Docker + debugpy + VSCode + PostgreSQL + DBeaver 開発用セットアップ  
Author: Kazuaki Watanabe

---

# 0. 概要

このドキュメントは、Odoo 19 をローカル環境で快適にデバッグ開発できるように構築するための完全ガイドです。

構成要素：

- Docker / Docker Compose
- PostgreSQL 16
- VSCode + debugpy（ブレークポイントデバッグ）
- custom_addons による Odoo モジュール開発
- DBeaver などの GUI による DB 接続

---

# 1. ディレクトリ構成

以下のようなディレクトリ構成で作業します：

./odoo_dev
├─ docker-compose.yml
├─ Dockerfile.debug
├─ config
│ └─ odoo.conf
├─ custom_addons
└─ .vscode
└─ launch.json


---

# 2. Dockerfile.debug の作成

Odoo を debugpy 経由で起動し、VSCode のブレークポイントで停止できるようにします。

`Dockerfile.debug`

```dockerfile
FROM odoo:19.0

# debugpy のインストール（PEP 668 回避のため --break-system-packages を使用）
RUN pip install --break-system-packages debugpy

# debugpy 経由で Odoo を起動
CMD python3 -m debugpy \
    --listen 0.0.0.0:5678 \
    --wait-for-client \
    -m odoo \
    -c /etc/odoo/odoo.conf \
    --dev=all

3. docker-compose.yml（完全版）

Odoo・PostgreSQL・debugpy のすべてを統合した完全版です。

services:

  db:
    image: postgres:16
    container_name: odoo19-db
    environment:
      POSTGRES_DB: odoo
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: odoo
    ports:
      - "5432:5432"          # DBeaver からの接続用
    volumes:
      - db-data:/var/lib/postgresql/data
    restart: unless-stopped

  odoo:
    build:
      context: .
      dockerfile: Dockerfile.debug
    container_name: odoo19-web
    depends_on:
      - db
    environment:
      HOST: db
      USER: odoo
      PASSWORD: odoo
    ports:
      - "8069:8069"          # Web ブラウザ
      - "5678:5678"          # debugpy（VSCode デバッグ）
    volumes:
      - odoo-data:/var/lib/odoo
      - ./config:/etc/odoo
      - ./custom_addons:/mnt/extra-addons
    restart: unless-stopped

volumes:
  db-data:
  odoo-data:


4. Odoo の設定ファイル（odoo.conf）

config/odoo.conf

[options]
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
data_dir = /var/lib/odoo
db_host = db
db_port = 5432
db_user = odoo
db_password = odoo
admin_passwd = admin
dbfilter = .*


5. Docker コンテナの起動

cd ./odoo_dev
docker compose up -d

ブラウザで確認：

http://localhost:8069


6. 初回のみ必要：データベースの初期化

Odoo が DB テーブルを作成していない状態だと 500 エラーが出るため、初回だけ次を実行：

docker compose stop odoo

docker compose run --rm odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d odoo \
  -i base \
  --stop-after-init

docker compose up -d


8. VSCode デバッグ実行方法

8-1. VSCode で ./odoo_dev を開く

8-2. 左の虫アイコン「Run and Debug」をクリック

8-3. Attach to Odoo (Docker debugpy) を選択

8-4. ブレークポイントを設定

8-5. ブラウザで Odoo を開く

8-6. 該当処理に到達すると VSCode 停止



9. PostgreSQL を DBeaver で見る方法

docker-compose.yml で 5432 を公開しているため接続できます。


| 項目       | 値         |
| -------- | --------- |
| Host     | localhost |
| Port     | 5432      |
| Database | odoo      |
| Username | odoo      |
| Password | odoo      |



10. よく使う Docker コマンド

起動

docker compose up -d

停止
docker compose down

再起動
docker compose restart odoo

完全初期化（DBデータも消す）
docker compose down -v


11. トラブルシューティング

❌ 500 Internal Server Error
原因：DB 初期化されていない
→ base モジュールをインストールする（6 の手順）

❌ KeyError: 'ir.http'
DB が空のため起こるエラー。
→ 初期化処理により解消。

❌ debugpy のブレークポイントで止まらない
・VSCode で Attach を実行していない
・Docker コンテナ起動前に VSCode を attach している
・custom_addons の pathMappings がずれている


12. 開発の次ステップ

・custom_addons に新モジュール作成
・Python モデル（models/*.py）を作成
・XML view（views/*.xml）作成
・メニュー追加
・ORM を使った機能追加
・デバッグでステップ実行


13. 完成！

このセットアップにより、Odoo 開発のベストプラクティスである
✔ ブレークポイントデバッグ
✔ DB GUI 管理
✔ コンテナ再現性の高い環境
✔ ソースコード管理が容易
がすべて満たされます。
