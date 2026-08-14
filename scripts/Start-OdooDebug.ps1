<#
    Start-OdooDebug.ps1  （Odoo 開発環境起動スクリプト）
    -------------------------------------------------------------

    ■ このスクリプトの目的：
        - docker-compose.yml を利用して
          「PostgreSQL（DB）」＋「Odoo（debugpy）」の2つのコンテナを起動する
        - Odoo は Dockerfile.debug を使ってビルドされ、VSCode からデバッグ可能になる
        - DBを完全初期化（リセット）した状態でも起動できるようにする

    ■ このスクリプトを置く場所：
        .\project root\scripts\Start-OdooDebug.ps1

    ■ プロジェクト構成（例）：
        .\odoo_dev\
            ├─ docker-compose.yml
            ├─ Dockerfile.debug
            ├─ config\
            ├─ custom_addons\
            └─ scripts\
                └─ Start-OdooDebug.ps1   ← このスクリプト

    ■ 使い方（PowerShell）：
        PS> cd C:\GitLab\odoo\odoo_dev\scripts

        # 通常起動
        PS> .\Start-OdooDebug.ps1

        # Odoo イメージをビルドし直して起動
        PS> .\Start-OdooDebug.ps1 -Rebuild

        # DB（PostgreSQL）を完全リセットして起動
        PS> .\Start-OdooDebug.ps1 -ResetDb

        # DBリセット＋再ビルド＋起動
        PS> .\Start-OdooDebug.ps1 -ResetDb -Rebuild

    -------------------------------------------------------------
#>

[CmdletBinding()]
param(
    # Odoo イメージを再ビルドするか？
    [switch]$Rebuild,

    # DB（PostgreSQL）のデータ永続化ボリュームごと初期化するか？
    [switch]$ResetDb
)

# -------------------------------------------------------------------------
# 1. スクリプトの実行場所を「プロジェクトルート」に自動変更する
# -------------------------------------------------------------------------
#   Point:
#     ・Start-OdooDebug.ps1 は /scripts に置いてあるため、
#       docker-compose.yml のある1階層上（親フォルダ）へ移動する必要がある。
#     ・$PSScriptRoot は「このスクリプトのあるフォルダ」を指す。
#     ・Join-Path $PSScriptRoot ".." → 親ディレクトリを取得する。
# -------------------------------------------------------------------------

$projectRoot = Join-Path $PSScriptRoot ".."
Set-Location -Path $projectRoot

Write-Host "プロジェクトルートに移動しました: $projectRoot" -ForegroundColor Cyan


# -------------------------------------------------------------------------
# 2. 使用する compose ファイル名
# -------------------------------------------------------------------------
$composeFile = "docker-compose.yml"


# -------------------------------------------------------------------------
# 3. DB完全リセットが指定された場合：コンテナとボリュームを削除
# -------------------------------------------------------------------------
#   Point:
#     ・"docker compose down -v" はコンテナとデータボリュームを完全削除する
#     ・リセットすることで、Odoo の DB を完全な初期状態に戻せる
# -------------------------------------------------------------------------
if ($ResetDb) {
    Write-Host "`n[1/3] DBリセット: 既存コンテナ + ボリュームを削除します..." -ForegroundColor Yellow
    docker compose -f $composeFile down -v
}


# -------------------------------------------------------------------------
# 4. Rebuild が指定された場合：Odoo のイメージを再ビルドする
# -------------------------------------------------------------------------
#   Point:
#     ・Dockerfile.debug を修正した場合や custom_addons を変更した場合、
#       ここでビルドし直す必要がある。
# -------------------------------------------------------------------------
if ($Rebuild) {
    Write-Host "`n[2/3] Odoo イメージを再ビルド中..." -ForegroundColor Yellow
    docker compose -f $composeFile build
}


# -------------------------------------------------------------------------
# 5. コンテナを起動する（バックグラウンドで up -d）
# -------------------------------------------------------------------------
#   Point:
#     ・PostgreSQL → Odoo の順で起動する（depends_on により）
#     ・Odoo は debugpy ポート（5678）で VSCode から接続できる
# -------------------------------------------------------------------------
Write-Host "`n[3/3] コンテナ起動中..." -ForegroundColor Yellow
docker compose -f $composeFile up -d


# -------------------------------------------------------------------------
# 6. 起動結果を表示する
# -------------------------------------------------------------------------
Write-Host "`n=== 現在起動中のコンテナ一覧 ===" -ForegroundColor Cyan
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host "`n🎉 Odoo デバッグ環境が起動しました！" -ForegroundColor Green
Write-Host "📌 ブラウザ: http://localhost:8069" -ForegroundColor Green
Write-Host "🐞 VSCode debugger: ポート 5678 に Attach" -ForegroundColor Green
Write-Host "`n必要であれば Stop-OdooDebug.ps1 も作成できます。" -ForegroundColor Green
