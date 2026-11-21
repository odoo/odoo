# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Real Estate Accounting",
    "summary": "Invoice the agency's fees when a property is sold",
    "category": "Real Estate/Brokerage",
    # A link module: it only makes sense when both the estate and account addons are installed
    "depends": ["estate", "account"],
    # Installed automatically as soon as all its dependencies are installed
    "auto_install": True,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
