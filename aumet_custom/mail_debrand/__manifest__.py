# Copyright 2016 Tecnativa - Jairo Llopis
# Copyright 2017 Tecnativa - Pedro M. Baeza
# Copyright 2019 Eficent Business and IT Consulting Services S.L.
#   - Lois Rilo <lois.rilo@eficent.com>
# 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Mail Debrand",
    "summary": """Remove Odoo branding in sent emails
    Removes anchor <a href odoo.com togheder with it's parent
    ( for powerd by) form all the templates
    removes any 'odoo' that are in tempalte texts > 20characters
    """,
    "version": "14.0.2.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": """Tecnativa, Eficent, Onestein, Sodexis, Nexterp Romania,
             Odoo Community Association (OCA)""",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail"],
    "development_status": "Production/Stable",
    "maintainers": ["pedrobaeza"],
}
