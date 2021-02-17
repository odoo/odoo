# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseReportEmail(models.TransientModel):
    _inherit = 'report.stock.inventory.wizard'

    partner_ids = fields.Many2many('res.partner', string='Send by Mail')

    def send_email(self):
        template_id = self.env.ref('email_attachment.product_movement_report_email_template').id
        self.print_report()
        print(f"\n\ntemplateid- - -{template_id}")
        self.env['mail.template'].browse(template_id).send_mail(self.id, force_send=True)
