############################################################
# 結論（このDockerfileでやりたいこと）
# ----------------------------------------------------------
# - Odoo本体だけをコンテナで動かす
# - PostgreSQLはRailway側の別サービス(PostgreSQL)を使用する
# - DB接続情報は環境変数(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD)で渡す
# - Web公開ポートは、Railwayが付与するPORT環境変数を使う
#
# ＝ Dockerfileには「Odooのみ」、PostgreSQLは「RailwayのマネージドDB」
############################################################

# Odoo 19 の公式イメージをベースにする
FROM odoo:19.0

# Odoo が読み込む設定ファイルのパスを指定
# （必要に応じて /etc/odoo/odoo.conf に自前の設定をマウントする前提）
ENV ODOO_RC=/etc/odoo/odoo.conf

# コンテナ起動時に実行するコマンド
# - --http-port に Railway の PORT 環境変数を使用
#   - Railway 側が自動で PORT を割り当ててくれる
#   - 未設定の場合はデフォルトで 8069 を使用
# - --db_host / --db_port / --db_user / --db_password は
#   Railway の PostgreSQL サービスから取得した値を環境変数で渡す想定
#
# 【重要】
#   - PostgreSQL 自体はこのコンテナ内には存在しない
#   - Railway で追加した PostgreSQL サービスに対してTCP接続する
CMD ["sh", "-c", "\
odoo \
  -c /etc/odoo/odoo.conf \
  --http-port ${PORT:-8069} \
  --db_host=$DB_HOST \
  --db_port=${DB_PORT:-5432} \
  --db_user=$DB_USER \
  --db_password=$DB_PASSWORD \
"]
