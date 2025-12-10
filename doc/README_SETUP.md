# Odoo 開発 / 本番（Cloud Run）構成ガイド

このプロジェクトでは、Odoo 19 を **開発用 Docker（debug / ホットリロード）** と  
**本番用 Cloud Run（外部DB + 安定運用）** の2つの環境で運用します。

- 開発：`Dockerfile.debug` + `docker-compose.dev.yml`
- 本番：`Dockerfile.prod` + Cloud Run（+ `docker-compose.prod.yml` でローカル検証）

さらに、この構成を前提とした **CI/CD（Cloud Build / GitHub Actions）** の例も載せています。

---

## 📁 ディレクトリ構成

```text
odoo_root/
├─ Dockerfile.debug          # 開発用（debugpy + --dev=all）
├─ Dockerfile.prod           # 本番用（Cloud Run 最適化）
├─ docker-compose.dev.yml    # 開発用（Postgres 内蔵）
├─ docker-compose.prod.yml   # 本番相当のローカルテスト用
├─ config/
│   └─ odoo.conf             # 共通の Odoo 設定
└─ custom_addons/
    └─ employee_portal/      # カスタムアドオン（開発対象）
1. 開発環境（Dev）
1-1. アーキテクチャ（Mermaid）
mermaid
コードをコピーする
flowchart LR
    subgraph DeveloperPC[Developer PC]
        VSCode[VSCode\n(ブレークポイント デバッグ)]
        DockerCompose[docker-compose.dev.yml]
    end

    DockerCompose --> OdooDebug[Odoo コンテナ\n(Dockerfile.debug)\n--dev=all + debugpy]
    DockerCompose --> DB[(PostgreSQL 16 コンテナ)]

    VSCode <--5678--> OdooDebug
    OdooDebug -->|接続| DB

    OdooDebug <--vol mount--> CustomAddons[/custom_addons/]
    OdooDebug <--vol mount--> OdooConf[/config/odoo.conf/]

    OdooDebug --> Browser[(http://localhost:8069)]
1-2. アーキテクチャ（PlantUML）
plantuml
コードをコピーする
@startuml
skinparam participantStyle rectangle

actor Developer
node "Developer PC" {
    component "VSCode\n(debugpy client)" as VSCode
    component "docker-compose.dev.yml" as ComposeDev
}

node "Docker Host" {
    node "Docker" {
        component "Odoo コンテナ\n(Dockerfile.debug)\n--dev=all + debugpy" as OdooDebug
        database "PostgreSQL 16\nコンテナ" as DB
    }
}

Developer --> VSCode
Developer --> ComposeDev

ComposeDev --> OdooDebug
ComposeDev --> DB

VSCode <--> OdooDebug : TCP 5678\n(debugpy attach)
OdooDebug --> DB : PostgreSQL\n(port 5432)

rectangle "Volume Mount" {
    OdooDebug -- "config/odoo.conf"
    OdooDebug -- "custom_addons/*"
}

Developer --> OdooDebug : HTTP 8069\n(ブラウザ)
@enduml
1-3. Dockerfile.debug
dockerfile
コードをコピーする
FROM odoo:19.0

# debugpy インストール（PEP 668 対応）
RUN pip install --break-system-packages debugpy

# VSCode から接続可能な debugpy を起動
CMD python3 -m debugpy \
    --listen 0.0.0.0:5678 \
    --wait-for-client \
    -m odoo \
    -c /etc/odoo/odoo.conf \
    --dev=all
1-4. docker-compose.dev.yml
yaml
コードをコピーする
version: "3.9"

services:
  db:
    image: postgres:16
    container_name: odoo19-db
    environment:
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: odoo
      POSTGRES_DB: odoo
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U odoo -d odoo"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  odoo-debug:
    build:
      context: .
      dockerfile: Dockerfile.debug
    container_name: odoo19-web-debug
    depends_on:
      db:
        condition: service_healthy
    environment:
      HOST: db
      USER: odoo
      PASSWORD: odoo
      ODOO_EXTRA_ADDONS: /mnt/extra-addons
    ports:
      - "8069:8069"   # Odoo Web
      - "5678:5678"   # debugpy
    volumes:
      - odoo-data:/var/lib/odoo
      - ./config:/etc/odoo
      - ./custom_addons:/mnt/extra-addons
    restart: unless-stopped

volumes:
  db-data:
  odoo-data:
1-5. VSCode デバッグ設定（launch.json）
json
コードをコピーする
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Attach to Odoo (debugpy in Docker)",
      "type": "debugpy",
      "request": "attach",
      "connect": { "host": "localhost", "port": 5678 },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}/custom_addons",
          "remoteRoot": "/mnt/extra-addons"
        }
      ]
    }
  ]
}
2. 本番環境（Prod / Cloud Run）
2-1. アーキテクチャ（Mermaid）
mermaid
コードをコピーする
flowchart LR
    subgraph BuildEnv[Build 環境]
        Config[/config/odoo.conf/]
        Addons[/custom_addons/]
        DockerfileProd[Dockerfile.prod]
    end

    Config --> DockerfileProd
    Addons --> DockerfileProd
    DockerfileProd -->|docker build| OdooImage[(Odoo イメージ)]

    subgraph CloudRun[Cloud Run]
        OdooProd[Odoo コンテナ\n(Dockerfile.prod)]
    end

    subgraph CloudSQLBlock[外部 DB]
        CloudSQL[(Cloud SQL / PostgreSQL)]
    end

    OdooImage --> OdooProd
    OdooProd --> CloudSQL
    UserBrowser[(ユーザーのブラウザ)] --> OdooProd
2-2. アーキテクチャ（PlantUML）
pl
コードをコピーする
@startuml
skinparam participantStyle rectangle

node "Build Environment" {
    file "config/odoo.conf" as Conf
    folder "custom_addons" as Addons
    file "Dockerfile.prod" as DFProd
}

DFProd <- Conf
DFProd <- Addons

DFProd --> OdooImage : docker build\n(Odoo 本番イメージ)

cloud "GCP" {
    node "Cloud Run" {
        component "Odoo コンテナ\n(Dockerfile.prod)" as OdooProd
    }

    database "Cloud SQL\n(PostgreSQL)" as CloudSQL
}

OdooImage --> OdooProd
OdooProd --> CloudSQL : PostgreSQL 接続

actor User as EndUser
EndUser --> OdooProd : HTTPS (PORT)
@enduml
2-3. Dockerfile.prod（Cloud Run 用）
dockerfile
コードをコピーする
FROM odoo:19.0

ENV ODOO_RC=/etc/odoo/odoo.conf \
    ODOO_EXTRA_ADDONS=/mnt/extra-addons \
    PYTHONUNBUFFERED=1

COPY config/odoo.conf /etc/odoo/odoo.conf
COPY custom_addons /mnt/extra-addons

RUN chown -R odoo:odoo /etc/odoo /mnt/extra-addons
USER odoo

CMD ["sh", "-c", "\
  odoo -c ${ODOO_RC} \
       --http-port=${PORT:-8069} \
       --http-interface=0.0.0.0 \
       --db_host=${DB_HOST} \
       --db_port=${DB_PORT:-5432} \
       --db_user=${DB_USER} \
       --db_password=${DB_PASSWORD} \
       --db_name=odoo \
"]
2-4. docker-compose.prod.yml（本番相当のローカル検証）
yaml
コードをコピーする
version: "3.9"

services:
  db:
    image: postgres:16
    container_name: odoo19-db-prod
    environment:
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: odoo
      POSTGRES_DB: odoo
    volumes:
      - db-data-prod:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U odoo -d odoo"]
      interval: 10s
      timeout: 5s
      retries: 10
    restart: always

  odoo:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: odoo19-web-prod
    depends_on:
      db:
        condition: service_healthy
    environment:
      HOST: db
      USER: odoo
      PASSWORD: odoo
      ODOO_EXTRA_ADDONS: /mnt/extra-addons
      DB_HOST: db
      DB_PORT: 5432
      DB_USER: odoo
      DB_PASSWORD: odoo
    ports:
      - "8069:8069"
    volumes:
      - odoo-data-prod:/var/lib/odoo
      - ./config:/etc/odoo:ro
      - ./custom_addons:/mnt/extra-addons:ro
    restart: always

volumes:
  db-data-prod:
  odoo-data-prod:
3. 開発 vs 本番 比較
項目	開発 (dev)	本番 (prod / Cloud Run)
Dockerfile	Dockerfile.debug	Dockerfile.prod
デバッガ	debugpy 有効	無効
--dev=all	有効（ホットリロード）	無効
DB	ローカル Postgres コンテナ	Cloud SQL / 外部 PostgreSQL
config / custom_addons	volume マウント（編集即反映）	イメージにコピー（デプロイ単位で固定）
再起動影響	影響小（開発用）	影響大（本番用・安定性優先）
用途	ローカル開発・デバッグ・動作確認	本番運用・ステージング

4. CI/CD 構成
ここからは、上記 Dockerfile を使って 自動ビルド & デプロイ する例です。

GCP: Cloud Build → Cloud Run

GitHub: GitHub Actions → Cloud Run

4-1. CI/CD 全体像（Mermaid）
mermaid
コードをコピーする
flowchart LR
    Dev[Developer\n(Git push)] --> Repo[(Git Repository)]

    subgraph CI[CI (Cloud Build / GitHub Actions)]
        BuildStep[Docker Build\n(Dockerfile.prod)]
        PushStep[Push to Registry\n(Artifact Registry / GHCR)]
        DeployStep[Deploy to Cloud Run]
    end

    Repo --> CI
    CI --> BuildStep --> PushStep --> DeployStep

    DeployStep --> CloudRunSvc[Cloud Run Service\n(Odoo)]
    CloudRunSvc --> CloudSQL[(Cloud SQL / PostgreSQL)]
4-2. CI/CD 全体像（PlantUML）
plantuml
コードをコピーする
@startuml
skinparam participantStyle rectangle

actor Dev as Developer

rectangle "Git Repository" as Repo

cloud "CI" {
  component "Cloud Build\nor\nGitHub Actions" as CI
}

node "Artifact Registry / Container Registry" as Registry
node "Cloud Run" as CR
database "Cloud SQL\n(PostgreSQL)" as SQL

Developer --> Repo : git push
Repo --> CI : トリガー\n(ブランチ / タグ)

CI --> CI : Docker build\n(Dockerfile.prod)
CI --> Registry : docker push\n(Odoo 本番イメージ)
CI --> CR : gcloud run deploy\n(新イメージ)

CR --> SQL : DB 接続\n(DB_HOST/USER/PASSWORD)
@enduml
4-3. Cloud Build の例（cloudbuild.yaml）
cloudbuild.yaml（GCP の Cloud Build 用）

yaml
コードをコピーする
steps:
  # 1) Docker ビルド
  - name: gcr.io/cloud-builders/docker
    args:
      - build
      - '-t'
      - 'asia-northeast1-docker.pkg.dev/PROJECT_ID/REPO_NAME/odoo-prod:latest'
      - '-f'
      - Dockerfile.prod
      - '.'

  # 2) Artifact Registry へ push
  - name: gcr.io/cloud-builders/docker
    args:
      - push
      - 'asia-northeast1-docker.pkg.dev/PROJECT_ID/REPO_NAME/odoo-prod:latest'

  # 3) Cloud Run へデプロイ
  - name: gcr.io/cloud-builders/gcloud
    args:
      - run
      - deploy
      - odoo-prod
      - '--image=asia-northeast1-docker.pkg.dev/PROJECT_ID/REPO_NAME/odoo-prod:latest'
      - '--region=asia-northeast1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--set-env-vars'
      - 'DB_HOST=xxx,DB_USER=xxx,DB_PASSWORD=xxx,DB_PORT=5432'

images:
  - asia-northeast1-docker.pkg.dev/PROJECT_ID/REPO_NAME/odoo-prod:latest
※ PROJECT_ID, REPO_NAME, DB_HOST などは実環境に合わせて変更。

4-4. GitHub Actions の例（.github/workflows/deploy.yml）
/.github/workflows/deploy.yml

yaml
コードをコピーする
name: Deploy Odoo to Cloud Run

on:
  push:
    branches:
      - main   # or production branch

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    env:
      PROJECT_ID: your-gcp-project-id
      REGION: asia-northeast1
      REPO_NAME: odoo
      SERVICE_NAME: odoo-prod
      IMAGE_NAME: asia-northeast1-docker.pkg.dev/your-gcp-project-id/odoo/odoo-prod:latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up gcloud
        uses: google-github-actions/setup-gcloud@v2
        with:
          project_id: ${{ env.PROJECT_ID }}
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          export_default_credentials: true

      - name: Build Docker image
        run: |
          docker build -t $IMAGE_NAME -f Dockerfile.prod .

      - name: Push image to Artifact Registry
        run: |
          gcloud auth configure-docker asia-northeast1-docker.pkg.dev -q
          docker push $IMAGE_NAME

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy $SERVICE_NAME \
            --image $IMAGE_NAME \
            --region $REGION \
            --platform managed \
            --allow-unauthenticated \
            --set-env-vars DB_HOST=${{ secrets.DB_HOST }},DB_USER=${{ secrets.DB_USER }},DB_PASSWORD=${{ secrets.DB_PASSWORD }},DB_PORT=5432
ポイント：

GCP のサービスアカウントキーを GCP_SA_KEY として GitHub Secrets に登録

DB 接続情報（DB_HOST, DB_USER, DB_PASSWORD）も Secrets に持たせる

5. 開発開始〜デプロイまでの最低限フロー
ローカル開発開始

bash
コードをコピーする
docker compose -f docker-compose.dev.yml up -d
http://localhost:8069 で動作確認

VSCode から debugpy にアタッチ

本番動作をローカル検証

bash
コードをコピーする
docker compose -f docker-compose.prod.yml up -d
Git push → CI/CD により Cloud Run 自動デプロイ

Cloud Build or GitHub Actions が Dockerfile.prod をビルド

Artifact Registry に push

Cloud Run へ gcloud run deploy