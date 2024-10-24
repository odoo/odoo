# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)

        if view_type == 'form':
            for node in arch.xpath("//field[@name='street']"):
                node.set('widget', 'address_autocomplete')
        return arch, view
