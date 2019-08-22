from odoo import models, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.model
    def _get_sequence_prefix(self, code, refund=False):
        """For peruvian companies we can not use sequences with **/** due to the edi generation which need in the
        sequence a plain text ended by a *-* and the length of this prefix"""
        if self.env.company.country_id != self.env.ref('base.pe'):
            return super()._get_sequence_prefix(code, refund=refund)
        prefix = code.upper()
        if refund:
            prefix = 'R' + prefix[:-1]
        return prefix + '-'
