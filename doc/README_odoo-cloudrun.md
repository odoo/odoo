📘 Cloud Run + Odoo 自動停止・再開スクリプト 説明書（PowerShell版）

このドキュメントは、Google Cloud Run 上で動作する Odoo サービスを
ワンコマンドで「停止」「再開」「状態確認」できる PowerShell スクリプトの説明です。

Cloud Run には正式な「停止」機能はありませんが、
max-instances（最大インスタンス数）を 0 にすることで実質的に停止状態にできます。
このスクリプトは、その操作を自動化するためのものです。

📂 スクリプトファイル
odoo-cloudrun.ps1

🛠 提供される機能
アクション	説明
stop	Cloud Run サービスを停止（max-instances=0）
start	再開（max-instances=1などに設定）
status	サービスの状態（Ready, maxScale）を表示
📝 スクリプト内容
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("start", "stop", "status")]
    [string]$Action
)

############################################################
# 設定値（必要に応じて書き換えて下さい）
############################################################

$PROJECT_ID = "savvy-camp-465809-m3"
$REGION = "asia-northeast1"
$SERVICE_NAME = "odoo-service"

# 再開時の最大インスタンス数
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

🚀 使い方
1. スクリプトの保存

任意のフォルダに odoo-cloudrun.ps1 を保存します。

例：

C:\GitLab\odoo\scripts\

2. PowerShell でスクリプトのあるフォルダへ移動
cd C:\GitLab\odoo\scripts

▶ 実行方法
3-1. Cloud Run を 停止（max-instances=0）
.\odoo-cloudrun.ps1 -Action stop

効果

インスタンス数が 0 になり、完全に停止した状態になります

課金もほぼゼロになります（Cloud Run は0インスタンス時無料）

3-2. Cloud Run を 再開
.\odoo-cloudrun.ps1 -Action start

効果

インスタンス数が $START_MAX_INSTANCES（デフォルト1）に戻り
再びサービスが起動できる状態に戻ります

3-3. 状態確認
.\odoo-cloudrun.ps1 -Action status


例として以下を表示します：

Ready 状態（True/False）

maxScale（最大インスタンス数）

⚠ 注意：Action を省略するとエラーになります

このスクリプトは：

param(
    [Parameter(Mandatory = $true)]


となっているため Action の指定が必須です。

誤って Action を付けずに実行すると：

.\odoo-cloudrun.ps1


PowerShell から次のように問われます：

Supply values for the following parameters:
Action:


ここで 何も入力せず Enter を押すと、

argument "" does not belong to the set "start,stop,status"


というエラーになります。

💡 対策：デフォルト動作を status にしたい場合

スクリプトの param 部分を以下のように変更すると、

param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("start", "stop", "status")]
    [string]$Action = "status"
)


以下のように呼んだとき：

.\odoo-cloudrun.ps1


→ 自動で status が実行されるようになります。

🎯 まとめ

Cloud Run は正式な停止機能がない → max-instances=0 で実質停止

このスクリプトで stop / start / status を一括管理可能

PowerShell から簡単にサービス制御できて開発効率アップ

Action 引数は必須（または default 設定で省略も可）