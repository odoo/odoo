############################################################
# Cloud Run + Odoo 用 Dockerfile（シングルDB固定・最適化版）
# ----------------------------------------------------------
# - ベースは公式イメージ odoo:19.0 を使用
# - コンテナ内では Odoo 本体のみを動かす（PostgreSQL は外部：Cloud SQL）
# - DB 接続情報は環境変数(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD)で渡す
# - 使用する DB 名を「odoo」に固定（--db_name=odoo）
#   → Cloud Run 上で「1サービス = 1つのDB」というシンプルな構成にする
#   → 昨日のような「削除したDBにセッションが残ってエラー」問題を防ぎやすい
# - Web 公開ポートは Cloud Run が付与する PORT 環境変数を使う
#   （ローカルで試す時など PORT 未設定なら 8069 を使用）
############################################################

# Odoo 19 の公式 Docker イメージをベースにする
FROM odoo:19.0

# Cloud Run のログ収集と相性を良くするため、Python の出力をバッファリングしない
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
#     Cloud SQL（PostgreSQL）の接続情報を環境変数から受け取る前提
# - --db_name=odoo
#     使う DB を「odoo」に固定し、マルチDB運用によるトラブルを避ける
#
# 【重要】
#   - このコンテナ内に PostgreSQL は含まれない
#   - Cloud SQL インスタンス「odoo-postgres」などの外部DBに TCP接続する構成
CMD ["sh", "-c", "\
  odoo \
    -c ${ODOO_RC} \
    --http-port=${PORT:-8069} \
    --http-interface=0.0.0.0 \
    --db_host=${DB_HOST} \
    --db_port=${DB_PORT:-5432} \
    --db_user=${DB_USER} \
    --db_password=${DB_PASSWORD} \
    --db_name=odoo \
"]
