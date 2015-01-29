# -*- coding: utf-8 -*-

from openerp import _
from openerp import api, fields, models


class EmailTemplate(models.Model):
    _inherit = 'mail.template'

    theme_xml_id = fields.Char('Theme XML ID',
        help='Last selected theme used for designing template.')

    @api.multi
    def action_edit_html(self):
        self.ensure_one()
        action_id =  self.env.ref('mass_mailing.action_email_template_marketing').id
        url = '/website_mail/email_designer?model=mail.template&res_id=%d&action=%d&enable_editor=1' % (self.id, action_id)
        return {
            'name': _('Edit Template'),
            'type': 'ir.actions.act_url',
            'url': url + '&theme_id=%s' % (self.theme_xml_id) if self.theme_xml_id else url,
            'target': 'self',
        }
