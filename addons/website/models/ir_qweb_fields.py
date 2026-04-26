# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from markupsafe import Markup

from odoo import api, models, _
from odoo.addons.website.tools import add_form_signature


class IrQwebField(models.AbstractModel):
    _inherit = 'ir.qweb.field'

    # TODO this handles only fields, but not widgets, find a way for them
    # to use draft values as well
    @api.model
    def record_to_html(self, record, field_name, options):
        if self.env.context.get('draft_preview') and record:
            website_id = self.env.context.get('website_id')
            if website_id:
                draft = self.env['website.draft.field'].search([
                    ('website_id', '=', website_id),
                    ('res_model', '=', record._name),
                    ('res_id', '=', record.id),
                ], limit=1)
                if draft and draft.values and field_name in draft.values:
                    return self.value_to_html(draft.values[field_name], options)
        return super().record_to_html(record, field_name, options)


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

    @api.model
    def value_to_html(self, value, options):
        res = super().value_to_html(value, options)

        if res and '<form' in res:  # Efficient check
            # The usage of `fromstring`, `HTMLParser`, `tostring` and `Markup`
            # is replicating what is done in the `super()` implementation.
            body = etree.fromstring("<body>%s</body>" % res, etree.HTMLParser())[0]
            add_form_signature(body, self.sudo().env)
            res = Markup(etree.tostring(body, encoding='unicode', method='html')[6:-7])

        return res
