# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError

class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.ondelete(at_uninstall=False)
    def _unlink_mail_template(self):
        linked_templates = {
            template.name for template in self.env['loyalty.program'].search([]).mapped('mail_template_id')
        }

        if any(record.name in linked_templates for record in self):
            raise ValidationError(_(
                "You cannot delete this mail template as it is being use by another model."
            ))
