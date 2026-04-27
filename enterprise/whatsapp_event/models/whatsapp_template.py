# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv import expression


class WhatsappTemplate(models.Model):
    _inherit = 'whatsapp.template'

    @api.model
    def _search(self, domain, *args, **kwargs):
        """Context-based hack to filter reference field in a m2o search box to emulate a domain the ORM currently does not support.

        As we can not specify a domain on a reference field, we added a context
        key `filter_template_on_event` on the template reference field. If this
        key is set, we add our domain in the `domain` in the `_search`
        method to filter the WhatsApp templates.
        """
        if self.env.context.get('filter_template_on_event'):
            domain = expression.AND([[('model', '=', 'event.registration')], [('status', '=', 'approved')], domain])
        return super()._search(domain, *args, **kwargs)

    def unlink(self):
        res = super().unlink()
        domain = ('template_ref', 'in', [f"{template._name},{template.id}" for template in self])
        self.env['event.mail'].sudo().search([domain]).unlink()
        self.env['event.type.mail'].sudo().search([domain]).unlink()
        return res
