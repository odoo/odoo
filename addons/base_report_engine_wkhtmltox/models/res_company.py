# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    report_rendering_engine = fields.Selection(
        selection_add=[('wkhtmltopdf', 'WKHTML to PDF/Image')],
        ondelete={'wkhtmltopdf': 'set default'},
        default='wkhtmltopdf'
    )
