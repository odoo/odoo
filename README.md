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

## Cloud Run + Cloud SQL でのデプロイ

---

Google Cloud Run で Odoo を構築する手順の詳細は以下のドキュメントにまとめています。
このリポジトリでは、開発・運用のための追加ドキュメントを `docs/` 以下に整理しています。

## 📚 Additional Documentation (docs/)


### ☁ Cloud Run / Cloud SQL（GCP）
- Cloud Run + Cloud SQL セットアップガイド  
  👉 [`docs/README_SETUP.md`](docs/README_SETUP.md)

- Cloud Run 運用補足（アーキテクチャ・注意点など）  
  👉 [`docs/README_CLOUDRUN.md`](docs/README_CLOUDRUN.md)

- Cloud Run 自動停止/再開スクリプト  
  👉 [`docs/scripts/odoo-cloudrun.ps1`](docs/scripts/odoo-cloudrun.ps1)

### 🐳 Docker
- ローカルデバッグ（Dockerfile.debug）の使い方  
  👉 [`docs/README_DOCKER_DEBUG.md`](docs/README_DOCKER_DEBUG.md)

### 🧩 Odoo 開発（OWL / custom_addons）
- OWL チュートリアル（フロントエンド）  
  👉 [`docs/README_OWL_TUTORIAL.md`](docs/README_OWL_TUTORIAL.md)

- custom_addons のインストール手順  
  👉 [`docs/README_INSTALL_MODULE.md`](docs/README_INSTALL_MODULE.md)

---
