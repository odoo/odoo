# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    l10n_latam_document_type_id = fields.Many2one(
        related='move_id.l10n_latam_document_type_id',
        readonly=True,
        auto_join=True,
        store=True,
        index=True,
    )

    @api.multi
    def prepare_move_lines_for_reconciliation_widget(
            self, target_currency=False, target_date=False):
        """ Use display_name instead of name on getting account.move rec name,
        usefull on bank statements and partner debt reconcile
        TODO remove when changed in odoo
        """
        res = super(
            AccountMoveLine,
            self).prepare_move_lines_for_reconciliation_widget(
            target_currency=target_currency, target_date=target_date)
        for rec in res:
            line = self.browse(rec['id'])
            display_name = line.move_id.display_name or ''
            rec['name'] = (
                line.name and line.name != '/' and
                display_name + ': ' + line.name or
                display_name)
        return res
