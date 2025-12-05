############################################################
# Cloud Run + Odoo 用 Dockerfile（最適化版）
# ----------------------------------------------------------
# - ベースは公式イメージ odoo:19.0 を使用
# - コンテナ内では Odoo 本体のみを動かす
# - DB(PostgreSQL) は Cloud SQL など外部サービスを利用
# - DB 接続情報は環境変数(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD)で渡す
# - Web公開ポートは、Cloud Run が付与する PORT 環境変数を使用
# - Cloud Run のヘルスチェックに対応できるよう、0.0.0.0 で待受
############################################################

# Odoo 19 の公式 Docker イメージをベースにする
FROM odoo:19.0

# ログをバッファリングせずに標準出力へ出す（Cloud Run のログ収集と相性が良い）
ENV PYTHONUNBUFFERED=1

# Odoo が読み込む設定ファイルのパスを環境変数で指定
# （必要に応じて /etc/odoo/odoo.conf を COPY で上書き可能）
ENV ODOO_RC=/etc/odoo/odoo.conf

# ここでカスタムアドオンや設定ファイルを追加したい場合は COPY を使う
# 例）
# COPY ./config/odoo.conf /etc/odoo/odoo.conf
# COPY ./custom_addons /mnt/extra-addons

# コンテナ起動時に実行する Odoo コマンド
# - --http-port
#     Cloud Run が自動で設定する PORT 環境変数を使用
#     ローカル実行時など PORT 未設定なら 8069 を使用
# - --http-interface
#     Cloud Run のリクエストを受け取れるように 0.0.0.0 で待受
# - --db_host / --db_port / --db_user / --db_password
#     Cloud SQL や外部 PostgreSQL の接続情報を環境変数から受け取る前提
#
# 【重要】
#   - このコンテナ内に PostgreSQL は含まれない
#   - Cloud SQL（PostgreSQL）や別ホストの Postgres へ TCP 接続する構成
CMD ["sh", "-c", "\
  odoo \
    -c ${ODOO_RC} \
    --http-port=${PORT:-8069} \
    --http-interface=0.0.0.0 \
    --db_host=${DB_HOST} \
    --db_port=${DB_PORT:-5432} \
    --db_user=${DB_USER} \
    --db_password=${DB_PASSWORD} \
"]