# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrPayslipRunHsbcAutopayWizard(models.TransientModel):
    _name = 'hr.payslip.run.hsbc.autopay.wizard'
    _description = 'HR Payslip Run HSBC Autopay Wizard'

    def _default_file_name(self):
        payslip_run_id = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))
        return payslip_run_id.l10n_hk_autopay_export_first_batch_filename or payslip_run_id.name

    ref = fields.Char(string="First Party Reference", size=12)
    customer_ref = fields.Char(string="Customer Reference", size=35)
    autopay_type = fields.Selection(related='company_id.l10n_hk_autopay_type', string="Autopay Type", readonly=True)
    authorisation_type = fields.Selection(
        selection=[
            ('A', 'Pre-Authorised'),
            ('P', 'Instruction Level Authorisation'),
            ('F', 'File Level Authorisation'),
            ('V', 'File Level Authorisation with ability to view instructions')],
        string="Authorisation Type", default='A'
    )
    payment_date = fields.Date(string="Payment Date", required=True, default=fields.Date.today)
    batch_type = fields.Selection(selection=[('first', "First Batch"), ('second', "Second Batch")], string="Batch Type", required=True, default='first')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    digital_pic_id = fields.Char(string="Digital Picture ID", size=11)
    file_name = fields.Char(string="File Name", required=True, default=_default_file_name)
    payment_set_code = fields.Char(string='Payment Set Code', required=True, size=3)

    @api.constrains('payment_set_code')
    def _check_payment_set_code(self):
        for wizard in self:
            if len(wizard.payment_set_code) != 3:
                raise ValidationError(_("Payment Set Code length must be 3 letters."))

    def generate_hsbc_autopay_apc_file(self):
        payslip_run_id = self.env['hr.payslip.run'].browse(self.env.context['active_id'])
        payslips = payslip_run_id.mapped('slip_ids').filtered(lambda p: p.net_wage > 0)
        payslips.sudo()._create_apc_file(
            self.payment_date, self.payment_set_code, self.batch_type, self.ref, self.file_name,
            authorisation_type=self.authorisation_type,
            customer_ref=self.customer_ref,
            digital_pic_id=self.digital_pic_id,
        )
