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

    def unlink(self):
        res = super().unlink()
        domain = ('template_ref', 'in', [f"{template._name},{template.id}" for template in self])
        self.env['event.mail'].sudo().search([domain]).unlink()
        self.env['event.type.mail'].sudo().search([domain]).unlink()
        return res

    def _render_report_qweb_pdf(self, report, res_id):
        """
        Overriding the function here to send multiple tickets in a single pdf
        """
        if self.model == 'event.registration':
            registrations = self.env['event.registration'].browse(res_id)
            child_ids = registrations.child_ids.ids
            if child_ids:
                return self.env['ir.actions.report']._render_qweb_pdf(report, child_ids)
        return super()._render_report_qweb_pdf(report, res_id)
