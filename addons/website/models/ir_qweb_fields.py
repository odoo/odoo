# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.addons.website.tools import sign_website_forms


class IrQwebFieldContact(models.AbstractModel):
    _inherit = 'ir.qweb.field.contact'

    @api.model
    def get_available_options(self):
        options = super().get_available_options()
        options.update(
            website_description=dict(type='boolean', string=_('Display the website description')),
            UserBio=dict(type='boolean', string=_('Display the biography')),
            badges=dict(type='boolean', string=_('Display the badges'))
        )
        return options


class IrQwebFieldHtml(models.AbstractModel):
    _inherit = 'ir.qweb.field.html'

    def _post_processing_att(self, tag, attrib):
        self.env['ir.qweb']._copy_translate_attributes(attrib)
        return super()._post_processing_att(tag, attrib)

    @api.model
    def value_to_html(self, value, options):
        res = super().value_to_html(value, options)

        if res and '<form' in res:  # Efficient check
            res = sign_website_forms(res, self.sudo().env)

        return res
