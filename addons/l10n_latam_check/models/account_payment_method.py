from odoo import models, api, fields


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    code = fields.Selection(
        selection_add=[
            ('new_third_party_checks', 'new_third_party_checks'),
            ('in_third_party_checks', 'in_third_party_checks'),
            ('out_third_party_checks', 'out_third_party_checks'),
            ('return_third_party_checks', 'return_third_party_checks'),
            ('own_checks', 'own_checks'),
        ],
        ondelete={
            'new_third_party_checks': 'cascade',
            'in_third_party_checks': 'cascade',
            'out_third_party_checks': 'cascade',
            'return_third_party_checks': 'cascade',
            'own_checks': 'cascade',
        },
    )
    outstanding_payment_account_id = fields.Many2one(
        comodel_name='account.account',
        check_company=True,
        string='Outstanding Payment Account',
        domain="[('account_type', 'in', ('asset_current', 'liability_current'))]",
    )

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['new_third_party_checks'] = {'type': ('cash',)}
        res['in_third_party_checks'] = {'type': ('cash',)}
        res['out_third_party_checks'] = {'type': ('cash',)}
        res['return_third_party_checks'] = {'type': ('bank',)}
        res['own_checks'] = {'type': ('bank',)}
        return res
