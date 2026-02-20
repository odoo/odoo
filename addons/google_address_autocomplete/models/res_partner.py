from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form' and 'enforce_cities' in self.env['res.country']._fields:
            for node in (arch.xpath("//field[@name='street_name']")):
                node.set('widget', 'google_address_autocomplete')

        return arch, view
