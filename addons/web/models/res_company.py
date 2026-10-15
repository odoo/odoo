# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_logo_url(self):
        self.ensure_one()
        logo = self.sudo().logo_web
        return f'/logo.png?company={self.id}&unique={logo.checksum[:7] if logo else 0}'
