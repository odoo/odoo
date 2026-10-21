# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.fields import Domain


class SmsTemplate(models.Model):
    _inherit = 'sms.template'

    def _delete_extra(self):
        yield from super()._delete_extra()
        domain = Domain('template_ref', 'in', [f"{template._name},{template.id}" for template in self])
        yield self.env['event.mail'].search(domain)
        yield self.env['event.type.mail'].search(domain)
