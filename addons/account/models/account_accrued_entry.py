import json
from odoo import models, _


class AccruedEntryMixin(models.AbstractModel):
    _name = 'account.accrued.entry.mixin'
    _description = 'Account Accrued Entry Mixin'

    def _get_preview_data(self, record):
        return json.dumps({
            'groups_vals': [self.env['account.move']._move_dict_to_preview_vals(
                move_vals=record._get_move_vals(),
                currency_id=record.company_id.currency_id,
            )],
            'options': {
                'columns': [
                    {'field': 'account_id', 'label': _('Account')},
                    {'field': 'name', 'label': _('Label')},
                    {'field': 'debit', 'label': _('Debit'), 'class': 'text-end text-nowrap'},
                    {'field': 'credit', 'label': _('Credit'), 'class': 'text-end text-nowrap'},
                ],
            },
        })

    def _get_aml_vals(self, name, balance, account_id, **kwargs):
        values = {
            'name': name,
            'debit': balance if balance > 0.0 else 0.0,
            'credit': -balance if balance < 0.0 else 0.0,
            'account_id': account_id,
        }
        values.update(kwargs)
        return values

    def _get_move_vals(self):
        """ To be overriden as every accrued entry has their own specific process """
        return {}

    def create_and_reverse_move(self):
        move_vals = self._get_move_vals()
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        reverse_move = move._reverse_moves(default_values_list=[{'ref': _("Reversal of: %s", move.ref)}])
        reverse_move.action_post()
        return move, reverse_move
