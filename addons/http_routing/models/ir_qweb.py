# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _prepare_environment(self, values):
        irQweb = super()._prepare_environment(values)
        values['slug'] = self.env['ir.http']._slug
        values['unslug_url'] = self.env['ir.http']._unslug_url
        values['url_for'] = self.env['ir.http']._url_for
        values['url_localized'] = self.env['ir.http']._url_localized
        return irQweb
