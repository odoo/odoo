📘 Cloud Run + Cloud SQL + Odoo 19 構築手順（完全版）

Google Cloud Run 上で Odoo をサーバレス運用するための構築手順まとめ

🧭 全体構成図（概要）
[Cloud Run] ---(Cloud SQL Proxy 経由)--- [Cloud SQL(PostgreSQL)]
     │
     └── 公開URL → https://xxxxx.a.run.app/

※ Dockerfile で Odoo のみ実行  
※ PostgreSQL は Cloud SQL に分離しマネージド化  
※ DB は odoo の 1 つに固定して運用を簡略化

1️⃣ 事前準備
✔ 必要なもの

Google Cloud アカウント

gcloud CLI インストール済み

課金有効化（Cloud Run / Cloud SQL が必要）

2️⃣ GCP プロジェクト設定

プロジェクト一覧を確認：

gcloud projects list


使用するプロジェクトを設定：

gcloud config set project PROJECT_ID


例：

gcloud config set project savvy-camp-465809-m3

3️⃣ 必要 API を有効化
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  sqladmin.googleapis.com

4️⃣ Cloud SQL（PostgreSQL）作成
★ PostgreSQL 15 を作成：
gcloud sql instances create odoo-postgres \
 --database-version=POSTGRES_15 \
 --tier=db-f1-micro \
 --region=asia-northeast1

DB作成：
gcloud sql databases create odoo --instance=odoo-postgres

ユーザー作成：
gcloud sql users create odoo \
 --instance=odoo-postgres \
 --password="YOUR_PASSWORD"

Cloud SQL 接続名取得：
gcloud sql instances describe odoo-postgres \
 --format="value(connectionName)"


例：

savvy-camp-465809-m3:asia-northeast1:odoo-postgres

5️⃣ Artifact Registry 作成
gcloud artifacts repositories create odoo-repo \
 --repository-format=docker \
 --location=asia-northeast1 \
 --description="Odoo images"


※ すでに存在する場合は ALREADY_EXISTS が出るが問題なし。

6️⃣ Cloud Run 用 Dockerfile（最終版）

Dockerfile をプロジェクトルートへ配置：

############################################################
# Cloud Run + Odoo 用 Dockerfile（シングルDB固定・最適化版）
############################################################

FROM odoo:19.0
ENV PYTHONUNBUFFERED=1
ENV ODOO_RC=/etc/odoo/odoo.conf

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


ポイント：

PostgreSQL は Cloud SQL 外部接続（Cloud Run 内には DB を持たない）

--db_name=odoo により単一DB運用
→ DB削除によるキャッシュ崩壊事故を防ぐ

7️⃣ Docker イメージのビルド & Artifact Registry へ Push
gcloud builds submit --tag "asia-northeast1-docker.pkg.dev/savvy-camp-465809-m3/odoo-repo/odoo-image" .


成功すると Artifact Registry へイメージが保存される。

8️⃣ Cloud Run デプロイ
gcloud run deploy odoo-service \
 --image="asia-northeast1-docker.pkg.dev/savvy-camp-465809-m3/odoo-repo/odoo-image" \
 --platform=managed \
 --region=asia-northeast1 \
 --allow-unauthenticated \
 --add-cloudsql-instances="savvy-camp-465809-m3:asia-northeast1:odoo-postgres" \
 --set-env-vars="DB_HOST=/cloudsql/savvy-camp-465809-m3:asia-northeast1:odoo-postgres,DB_PORT=5432,DB_USER=odoo,DB_PASSWORD=YOUR_PASSWORD"


成功後 Cloud Run URL が表示される：

https://odoo-service-xxxxxx-uc.a.run.app

9️⃣ Odoo 初期セットアップ

上記 URL にアクセスし、以下を設定：

管理パスワード

モジュールの初期構成

🔟 Cloud Run の停止・再開自動化スクリプト（オプション）

odoo-cloudrun.ps1 を作成：

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("start","stop","status")]
    [string]$Action
)

$PROJECT_ID="savvy-camp-465809-m3"
$REGION="asia-northeast1"
$SERVICE_NAME="odoo-service"
$START_MAX_INSTANCES=1

function Ensure-GcloudProject {
  gcloud config set project $PROJECT_ID | Out-Null
}

function Get-CurrentConfig {
  gcloud run services describe $SERVICE_NAME --region=$REGION `
   --format="table(metadata.name,status.conditions[?type='Ready'].status,metadata.annotations['autoscaling.knative.dev/maxScale'])"
}

Ensure-GcloudProject

switch ($Action) {
 "stop" {
  gcloud run services update $SERVICE_NAME --region=$REGION --max-instances=0
  Get-CurrentConfig
 }
 "start" {
  gcloud run services update $SERVICE_NAME --region=$REGION --max-instances=$START_MAX_INSTANCES
  Get-CurrentConfig
 }
 "status" {
  Get-CurrentConfig
 }
}

実行方法：

停止：

.\odoo-cloudrun.ps1 -Action stop


再開：

.\odoo-cloudrun.ps1 -Action start


状態確認：

.\odoo-cloudrun.ps1 -Action status

🔧 よくあるトラブルと対策
❗ DB削除後に500/503が出る

→ セッションに古い DB が残るため

🔧 対策

シークレットウィンドウで再アクセス

Cookie削除

Cloud Run を stop → start でコンテナ再起動

DB を1つに固定（この構成では --db_name=odoo で解決）

🎯 まとめ：この構成のメリット

Cloud Run で Odoo を完全サーバレス運用可能

Cloud SQL で DB を安全に管理

デプロイが Dockerfile 1枚で完結

DB を固定することでトラブル激減

料金も最小限（Cloud Run 無負荷0円 + f1-micro）