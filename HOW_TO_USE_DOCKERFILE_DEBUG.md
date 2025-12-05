Dockerfile.debug をローカルで使用する方法

このドキュメントでは、ローカル環境で Dockerfile.debug（デバッグ用 Dockerfile）を利用する手順をまとめています。
本番（Railway 用）の Dockerfile とは切り替えて使用します。

📌 目的

開発時：Dockerfile.debug を使い リモートデバッグ（debugpy など）可能な Odoo を起動する

本番用：Dockerfile を使い、Railway 等で プロダクション構成として動かす

両方の環境を Docker コマンドだけで切り替えて利用できるようにする

🔧 1. デバッグ用イメージのビルド方法

Dockerfile.debug を使用する場合、-f オプションで Dockerfile を指定します。

docker build -t odoo-debug -f Dockerfile.debug .

-t の意味

作成するイメージに名前（タグ）を付ける
例：odoo-debug

🚀 2. デバッグ用コンテナの起動

デバッグ環境としてコンテナを起動します。

docker run --name odoo-debug \
  -p 8069:8069 \
  -p 5678:5678 \
  odoo-debug

よく使うポート
ポート	用途
8069	Odoo Web UI
5678	debugpy（VSCode のリモートデバッグ接続用）
🆚 3. 本番（プロダクション）用 Dockerfile との切り替え
本番用 Dockerfile からイメージをビルド
docker build -t odoo-prod -f Dockerfile .

本番用イメージの起動
docker run --name odoo-prod -p 8069:8069 odoo-prod

🔄 4. デバッグ環境と本番環境の併用

異なるポートにすれば 同時起動も可能です。

例：

用途	イメージ名	Webポート	デバッグポート
本番動作確認	odoo-prod	8069	なし
デバッグ用	odoo-debug	8070	5678

デバッグ環境を別ポートで起動する例：

docker run --name odoo-debug \
  -p 8070:8069 \
  -p 5678:5678 \
  odoo-debug

📁 5. docker-compose を使う方法（オプション）

複数の環境を使う場合、docker-compose.yml にまとめると便利です。

services:
  odoo-prod:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8069:8069"

  odoo-debug:
    build:
      context: .
      dockerfile: Dockerfile.debug
    ports:
      - "8070:8069"
      - "5678:5678"


実行：

docker compose up --build

🧹 6. コンテナ・イメージの削除
コンテナ削除
docker rm -f odoo-debug
docker rm -f odoo-prod

イメージ削除
docker rmi odoo-debug
docker rmi odoo-prod

✅ まとめ

Dockerfile.debug を使う場合は docker build -f で指定する

デバッグ環境では debugpyポート を公開して VSCode からアタッチ

プロダクション用イメージとはタグ（名前）を変えて管理

docker-compose を使うと複数環境を楽に切り替え可能