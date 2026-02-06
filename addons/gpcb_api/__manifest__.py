# Part of GPCB. See LICENSE file for full copyright and licensing details.
{
    'name': 'GPCB REST API',
    'version': '1.0',
    'category': 'Technical',
    'summary': 'REST API for POS integration, mobile apps, and external systems',
    'description': """
GPCB REST API
=============

Versioned REST API for integrating external systems with GPCB Accounting:

- **Invoice endpoints** — Create, confirm, cancel invoices with DIAN electronic invoicing
- **Partner endpoints** — Customer/supplier lookup and creation with NIT validation
- **Product endpoints** — Product/service catalog with tax information
- **Tax computation** — Real-time tax preview before invoice creation
- **POS session** — Session open/close/summary for point-of-sale terminals
- **Report endpoints** — Financial report data for mobile apps

Authentication uses Odoo's built-in API key system (Bearer token).
All endpoints are prefixed with ``/api/v1/``.
    """,
    'depends': [
        'account',
        'point_of_sale',
        'l10n_co_edi',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/gpcb_api_log_views.xml',
    ],
    'installable': True,
    'author': 'GPCB',
    'license': 'LGPL-3',
}
