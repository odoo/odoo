# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.model
    def _search(self, domain, *args, **kwargs):
        """Context-based hack to filter reference field in a m2o search box to emulate a domain the ORM currently does not support.

        As we can not specify a domain on a reference field, we added a context
        key `filter_template_on_event` on the template reference field. If this
        key is set, we add our domain in the `domain` in the `_search`
        method to filtrate the mail templates.
        """
        if self.env.context.get('filter_template_on_event'):
            domain = Domain('model', '=', 'event.registration') & Domain(domain)
        return super()._search(domain, *args, **kwargs)

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        if self._context.get('default_model', {}) == 'event.registration':
            result['email_from'] = "{{ (object.event_id.organizer_id.email_formatted or object.event_id.user_id.email_formatted or '') }}"
            result['email_to'] = '{{ (object.email and \'"%s" <%s>\' % (object.name, object.email) or object.partner_id.email_formatted or \'\') }}'
            result['lang'] = '{{ object.event_id.lang or object.partner_id.lang }}'
        return result

    def unlink(self):
        res = super().unlink()
        domain = ('template_ref', 'in', [f"{template._name},{template.id}" for template in self])
        self.env['event.mail'].sudo().search([domain]).unlink()
        self.env['event.type.mail'].sudo().search([domain]).unlink()
        return res
