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

## Docker Usage

This repository defines two different Compose files to keep local development
and production deployments separate:

- **docker-compose.yml** – the production-style configuration used by our
  GitHub workflow and on the VPS. It pulls the prebuilt image from
  `ghcr.io/laxya911/custom-odoo:feature-odoo-uber` and includes Traefik for
  HTTPS routing. Keep this file committed to the repo.

- **docker-compose.local.yml** – a helper file for building and running the
  stack locally. It only includes the `db` and `odoo` services, omits
  Traefik, and builds the image from the current workspace (`odoo_test:latest`).
  The file is listed in `.gitignore`/`.dockerignore` and should not be
  committed.

### Local development steps

1. Create a `.env.local` from `.env.example` and adjust credentials.
2. Run `docker compose --env-file .env.local -f docker-compose.local.yml up -d`.
3. The Odoo service will be accessible at <http://localhost:8069>.
4. When finished, stop with `docker compose -f docker-compose.local.yml down`.

### Production deployment

The CI/CD pipeline builds the image on merge to `19.0` and pushes it to GHCR.
On the VPS, a `docker compose up -d` (using the standard
`docker-compose.yml`) will pull the new image and start the services.

## Security

If you believe you have found a security issue, check our [Responsible Disclosure page](https://www.odoo.com/security-report)
for details and get in touch with us via email.
