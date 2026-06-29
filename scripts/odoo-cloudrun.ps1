param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("start", "stop", "status")]
    [string]$Action
)

############################################################
# 設定値（必要に応じて書き換えて下さい）
############################################################

# GCP プロジェクトID
$PROJECT_ID = "savvy-camp-465809-m3"

# Cloud Run のリージョン
$REGION = "asia-northeast1"

# Cloud Run のサービス名（今回の Odoo）
$SERVICE_NAME = "odoo-service"

# 再開時に設定したい最大インスタンス数
# 例: 開発用なら 1、本番で少し余裕を持たせるなら 2〜3 など
$START_MAX_INSTANCES = 1

############################################################
# 共通関数
############################################################

function Ensure-GcloudProject {
    Write-Host ">> gcloud プロジェクトを [$PROJECT_ID] に設定します..." -ForegroundColor Cyan
    gcloud config set project $PROJECT_ID | Out-Null
}

function Get-CurrentConfig {
    Write-Host ">> 現在の Cloud Run サービス設定を取得します..." -ForegroundColor Cyan
    gcloud run services describe $SERVICE_NAME `
        --region=$REGION `
        --format="table(metadata.name,status.conditions[?type='Ready'].status,metadata.annotations['autoscaling.knative.dev/maxScale'])"
}

############################################################
# メイン処理
############################################################

Ensure-GcloudProject

switch ($Action) {
    "stop" {
        Write-Host ">> Cloud Run サービス [$SERVICE_NAME] を停止（max-instances=0）します..." -ForegroundColor Yellow
        gcloud run services update $SERVICE_NAME `
            --region=$REGION `
            --max-instances=0

        Write-Host "`n>> 停止後の状態:" -ForegroundColor Green
        Get-CurrentConfig
    }

    "start" {
        Write-Host ">> Cloud Run サービス [$SERVICE_NAME] を再開（max-instances=$START_MAX_INSTANCES）します..." -ForegroundColor Yellow
        gcloud run services update $SERVICE_NAME `
            --region=$REGION `
            --max-instances=$START_MAX_INSTANCES

        Write-Host "`n>> 再開後の状態:" -ForegroundColor Green
        Get-CurrentConfig
    }

    "status" {
        Write-Host ">> Cloud Run サービス [$SERVICE_NAME] の状態を表示します..." -ForegroundColor Yellow
        Get-CurrentConfig
    }
}
