# Odoo

[![Build Status](https://runbot.odoo.com/runbot/badge/flat/1/master.svg)](https://runbot.odoo.com/runbot)
[![Tech Doc](https://img.shields.io/badge/master-docs-875A7B.svg?style=flat&colorA=8F8F8F)](https://www.odoo.com/documentation/master)
[![Help](https://img.shields.io/badge/master-help-875A7B.svg?style=flat&colorA=8F8F8F)](https://www.odoo.com/forum/help-1)
[![Nightly Builds](https://img.shields.io/badge/master-nightly-875A7B.svg?style=flat&colorA=8F8F8F)](https://nightly.odoo.com/)

Odoo is a suite of web based open source business apps.

The main Odoo Apps include an [Open Source CRM](https://www.odoo.com/page/crm),
[Website Builder](https://www.odoo.com/app/website),
[eCommerce](https://www.odoo.com/app/ecommerce),
[Warehouse Management](https://www.odoo.com/app/inventory),
[Project Management](https://www.odoo.com/app/project),
[Billing &amp; Accounting](https://www.odoo.com/app/accounting),
[Point of Sale](https://www.odoo.com/app/point-of-sale-shop),
[Human Resources](https://www.odoo.com/app/employees),
[Marketing](https://www.odoo.com/app/social-marketing),
[Manufacturing](https://www.odoo.com/app/manufacturing),
[...](https://www.odoo.com/)

Odoo Apps can be used as stand-alone applications, but they also integrate seamlessly so you get
a full-featured [Open Source ERP](https://www.odoo.com) when you install several Apps.

## Getting started with Odoo

For a standard installation please follow the [Setup instructions](https://www.odoo.com/documentation/master/administration/install/install.html)
from the documentation.

To learn the software, we recommend the [Odoo eLearning](https://www.odoo.com/slides),
or [Scale-up, the business game](https://www.odoo.com/page/scale-up-business-game).
Developers can start with [the developer tutorials](https://www.odoo.com/documentation/master/developer/howtos.html).

## Security

If you believe you have found a security issue, check our [Responsible Disclosure page](https://www.odoo.com/security-report)
for details and get in touch with us via email.


# 📚 Odoo ドキュメント索引（docs/README.md）

このディレクトリは、Odoo リポジトリの **開発・運用・デプロイ関連ドキュメント** をまとめたものです。  
カテゴリ別に参照したいドキュメントへジャンプできます。

---

## ☁ Cloud Run / Cloud SQL（GCP）

Odoo を Google Cloud 上にデプロイするためのドキュメントです。

- **Cloud Run + Cloud SQL セットアップ手順（完全版）**  
  Google Cloud Run と Cloud SQL(PostgreSQL) 上で Odoo 19 を動かすための構築手順。  
  👉 [`README_SETUP.md`](README_SETUP.md)

- **Cloud Run 運用メモ・補足ドキュメント**  
  Cloud Run の挙動、構成の考え方、運用上の注意点などをまとめたドキュメント。  
  👉 [`README_CLOUDRUN.md`](README_CLOUDRUN.md)

- **Cloud Run 自動停止 / 再開スクリプト（PowerShell）**  
  max-instances を切り替えて Cloud Run の「停止」「再開」「状態確認」を行うスクリプト。  
  👉 [`scripts/odoo-cloudrun.ps1`](scripts/odoo-cloudrun.ps1)

---

## 🐳 Docker / ローカル開発

ローカル環境でのデバッグ用 Dockerfile の使い方など。

- **Dockerfile.debug の使い方（ローカルデバッグ環境）**  
  `Dockerfile.debug` を使って、debugpy + VSCode で Odoo をデバッグする手順。  
  👉 [`README_DOCKER_DEBUG.md`](README_DOCKER_DEBUG.md)

---

## 🧩 Odoo 開発（フロントエンド / モジュール）

Odoo 19 の拡張に関するドキュメントです。

- **Odoo 19 OWL（フロントエンド）チュートリアル**  
  OWL コンポーネントの作り方、`web.assets_backend` への登録方法など、  
  フロント側の拡張方法を解説。  
  👉 [`README_OWL_TUTORIAL.md`](README_OWL_TUTORIAL.md)

- **custom_addons モジュールのインストール手順**  
  Docker 開発環境で `custom_addons` 配下のモジュールを読み込んでインストールする手順。  
  👉 [`README_INSTALL_MODULE.md`](README_INSTALL_MODULE.md)

---

## 🔧 メンテナンス方針

- 新しいドキュメントを追加した場合は、  
  1. `docs/` 配下に Markdown を追加  
  2. この `docs/README.md` にリンクを 1 行足す  
- スクリプト類は `docs/scripts/` にまとめて配置する想定です。

