# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SmsTemplate(models.Model):
    _inherit = 'sms.template'

    def unlink(self):
        res = super().unlink()
        domain = ('template_ref', 'in', [f"{template._name},{template.id}" for template in self])
        self.env['event.mail'].sudo().search([domain]).unlink()
        self.env['event.type.mail'].sudo().search([domain]).unlink()
        return res
