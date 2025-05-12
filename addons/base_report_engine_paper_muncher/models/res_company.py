# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    report_rendering_engine = fields.Selection(
        selection_add=[('paper-muncher', 'Paper Muncher')],
        ondelete={'paper-muncher': 'set default'},
    )
