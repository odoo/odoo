# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    l10n_au_payment_batch_id = fields.Many2one(
        'account.batch.payment', string='Payment Batch', readonly=True, copy=False
    )
    l10n_au_payment_batch_state = fields.Selection(related='l10n_au_payment_batch_id.state', tracking=False)
    l10n_au_stp_status = fields.Selection([
        ("draft", "Draft"),
        ("ready", "Ready"),
        ("sent", "Submitted"),
        ("error", "Error"),
    ], string="STP Status", compute="_compute_stp_status", help="Is the payslip ready for STP submission?")
    l10n_au_stp_count = fields.Integer(compute='_compute_stp_count')

    @api.depends('slip_ids', 'slip_ids.state')
    def _compute_stp_status(self):
        for run in self:
            run.l10n_au_stp_status = 'draft'
            if not run.slip_ids:
                continue
            elif all(payslip.l10n_au_stp_status == 'sent' for payslip in run.slip_ids):
                run.l10n_au_stp_status = 'sent'
            elif any(payslip.state == 'draft' for payslip in run.slip_ids):
                run.l10n_au_stp_status = 'draft'
            elif any(payslip.l10n_au_stp_status == 'error' for payslip in run.slip_ids):
                run.l10n_au_stp_status = 'error'
            elif all(payslip.l10n_au_stp_status == 'ready' for payslip in run.slip_ids):
                run.l10n_au_stp_status = 'ready'

    def _compute_stp_count(self):
        slip_stp = self.slip_ids._get_payslip_stp()
        for run in self:
            run.l10n_au_stp_count = len(self.env["l10n_au.stp"].union(*(slip_stp[slip.id] for slip in run.slip_ids)))

    def action_register_payment(self):
        self.ensure_one()
        if any(m.state != 'posted' for m in self.slip_ids.move_id):
            raise UserError(_("You can only register payment for posted journal entries."))
        if not self.slip_ids.struct_id.rule_ids.filtered(lambda r: r.code == "NET").account_credit.reconcile:
            raise UserError(_('The credit account on the NET salary rule is not reconciliable'))

        faulty_bank_accounts = self.slip_ids.employee_id.sudo().bank_account_id.filtered(lambda b: not b.allow_out_payment)
        if faulty_bank_accounts:
            raise RedirectWarning(
                message=_('Bank account(s) for the following employee(s) are not allowed for outgoing payments!\n%s',
                          '\n'.join(faulty_bank_accounts.partner_id.mapped('name'))),
                action=faulty_bank_accounts._get_records_action(),
                button_text=_('Configure Employee Bank Account'),
            )

        clearing_house = self.env.ref('l10n_au_hr_payroll_account.res_partner_clearing_house', raise_if_not_found=False)
        if not clearing_house:
            raise UserError(_("No clearing house record found for this company!"))
        super_account = clearing_house.property_account_payable_id

        bank_journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        aba_payment_method = bank_journal.outbound_payment_method_line_ids.filtered(lambda l: l.code == 'aba_ct')

        res = self.slip_ids.move_id.line_ids.filtered(lambda line: line.account_id != super_account)\
            .action_register_payment()
        res['context'].update({"default_payment_method_line_id": aba_payment_method.id})
        return res

    def action_open_payment_batch(self):
        return self.l10n_au_payment_batch_id._get_records_action()

    def action_post(self):
        self.slip_ids.move_id.action_post()

    def action_payment_report(self, export_format='aba'):
        action = super().action_payment_report()
        if self.company_id.country_code != 'AU':
            return action
        action.update({
            'context': {
                **action['context'],
                'default_export_format': export_format,
            },
        })
        return action

    def action_open_stp(self):
        return self.env["l10n_au.stp"]\
            .union(*self.slip_ids._get_payslip_stp().values())\
            ._get_records_action(name=_("Single Touch Payroll"))

    def _are_payslips_ready(self):
        ffr_stp_record = self.env['l10n_au.stp'].search_count([('payslip_batch_id', '=', self.id), ('ffr', '=', True)])
        if ffr_stp_record:
            # Allow to close the payslip run if some payslips are already paid in case of Full file replacement STP
            return all(slip.state in ['done', 'paid', 'cancel'] for slip in self.mapped('slip_ids'))
        return super()._are_payslips_ready()
