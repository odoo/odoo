# Copyright 2023 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import odoo
from odoo import api


def migrate(cr, installed_version):
    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
    env["mis.report.instance.period"].search([])._compute_source_aml_model_id()
