<# 
    Start-OdooDebug.ps1

    目的:
      - docker-compose.yml を使って
        PostgreSQL（db） と Odoo（odoo-debug） をまとめて起動する
      - オプションで「ビルドし直し」「DB完全リセット」もできるようにする

    使い方の例:
      1) 普通に起動:
         PS> .\Start-OdooDebug.ps1

      2) イメージをビルドし直してから起動:
         PS> .\Start-OdooDebug.ps1 -Rebuild

      3) DBボリュームも含めて完全リセットしてから起動:
         PS> .\Start-OdooDebug.ps1 -ResetDb

      ※ Docker Compose v2 を想定しているので "docker compose" を使用。
         v1 の場合は "docker-compose" に置き換えてください。
#>

[CmdletBinding()]
param(
    # イメージを再ビルドするかどうか
    [switch]$Rebuild,

    # DBボリュームを含めて完全リセットするかどうか
    [switch]$ResetDb
)

# --- スクリプトのある場所を基準ディレクトリにする -------------------------
# （どこから実行しても、この ps1 があるフォルダをカレントにする）
Set-Location -Path $PSScriptRoot

# --- 使用する compose ファイル名 --------------------------------------------
$composeFile = "docker-compose.yml"

Write-Host "=== Odoo Debug 環境 起動スクリプト ===" -ForegroundColor Cyan
Write-Host "compose ファイル: $composeFile" -ForegroundColor Cyan

# --- ResetDb 指定時: コンテナとボリュームを完全削除 ------------------------
if ($ResetDb) {
    Write-Host "`n[1/3] 既存コンテナとボリュームを削除します (docker compose down -v)..." -ForegroundColor Yellow
    docker compose -f $composeFile down -v
}

# --- Rebuild 指定時: イメージの再ビルド -------------------------------------
if ($Rebuild) {
    Write-Host "`n[2/3] イメージをビルドし直します (docker compose build)..." -ForegroundColor Yellow
    docker compose -f $composeFile build
}

# --- コンテナ起動 ------------------------------------------------------------
Write-Host "`n[3/3] コンテナをバックグラウンドで起動します (docker compose up -d)..." -ForegroundColor Yellow
docker compose -f $composeFile up -d

# --- 起動状況を表示 ----------------------------------------------------------
Write-Host "`n=== 起動中のコンテナ一覧 ===" -ForegroundColor Cyan
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

Write-Host "`n完了しました。ブラウザで http://localhost:8069 を開いてください。" -ForegroundColor Green
Write-Host "VSCode からはポート 5678 に 'Attach to Python' で接続します。" -ForegroundColor Green
