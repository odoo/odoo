# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

class res_company(models.Model):
    _inherit = "res.company"

    sepa_initiating_party_name = fields.Char('Initiating Party', size=70, default=lambda self: self.env.user.company_id.name,
        help="Will appear in SEPA payments as the name of the party initiating the payment.")


class account_journal(models.Model):
    _inherit = "account.journal"

    @api.one
    @api.depends('outbound_payment_methods')
    def _compute_sepa_payment_method_selected(self):
        self.sepa_payment_method_selected = any(pm.code == 'sepa_ct' for pm in self.outbound_payment_methods)

    sepa_payment_method_selected = fields.Boolean(compute='_compute_sepa_payment_method_selected')


class account_payment(models.Model):
    _inherit = "account.payment"


    # TODO: those fields are to be added to re_company or account_journal or account_payment

    # def _get_sepa_struct_communication_types(self):
    #     return [('ISO', 'ISO')]

    # sepa_priority = fields.Selection([('NORM', 'Normal'), ('HIGH', 'High')], string='Priority', default='NORM',
    #     help="Instruction Priority of the generated payment order.")
    # sepa_communication = fields.Char(size=140, required=True)
    # sepa_struct_communication_type = fields.Selection('_get_sepa_struct_communication_types', string='Structured Communication Type', default='ISO')
    # sepa_batch_booking = fields.Boolean('Batch Booking', help="If true, the bank statement will display only one credit line for all the direct "
    #     "debits of the SEPA file ; if false, the bank statement will display one credit line per direct debit of the SEPA file.")
    # sepa_charge_bearer = fields.selection([('SLEV', 'Following Service Level'), ('SHAR', 'Shared'), ('CRED', 'Borne by Creditor'), ('DEBT', 'Borne by Debtor')],
    #     string='Charge Bearer', default='SLEV', required=True)
