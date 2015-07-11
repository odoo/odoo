# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError

class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.one
    @api.depends('outbound_payment_method_ids')
    def _compute_check_writing_payment_method_selected(self):
        self.check_writing_payment_method_selected = any(pm.code == 'check_writing' for pm in self.outbound_payment_method_ids)

    @api.one
    @api.depends('check_manual_sequencing')
    def _get_check_next_number(self):
        if self.check_sequence_id:
            self.check_next_number = self.check_sequence_id.number_next_actual
        else:
            self.check_next_number = 1

    @api.one
    def _set_check_next_number(self):
        if self.check_next_number < self.check_sequence_id.number_next_actual:
            raise ValidationError(_("The last check number was %s. In order to avoid a check being rejected "
                "by the bank, you can only use a greater number." % self.check_sequence_id.number_next_actual))
        self.check_sequence_id.sudo().number_next_actual = self.check_next_number

    check_manual_sequencing = fields.Boolean('Manual Numbering', default=False,
        help="Check this option if your pre-printed checks are not numbered.")
    check_sequence_id = fields.Many2one('ir.sequence', 'Check Sequence', readonly=True, copy=False,
        help="Checks numbering sequence.")
    check_next_number = fields.Integer('Next Check Number', compute='_get_check_next_number', inverse='_set_check_next_number',
        help="Sequence number of the next printed check.")
    check_writing_payment_method_selected = fields.Boolean(compute='_compute_check_writing_payment_method_selected',
        help="Technical feature used to know whether check writing was enabled as payment method.")

    @api.model
    def create(self, vals):
        if not vals.get('check_sequence_id'):
            vals.update({'check_sequence_id': self._create_check_sequence(vals).id})
        return super(AccountJournal, self).create(vals)

    @api.one
    def copy(self, default=None):
        rec = super(AccountJournal, self).copy(default)
        rec.write({'check_sequence_id': self._create_check_sequence({'name': rec.name, 'company_id': rec.company_id.id}).id})
        return rec

    @api.model
    def _create_check_sequence(self, vals):
        """ Create a check sequence for the journal """
        return self.env['ir.sequence'].sudo().create({
            'name': vals['name'] + _(" : Check Number Sequence"),
            'implementation': 'no_gap',
            'padding': 5,
            'number_increment': 1,
            'company_id': vals.get('company_id', self.env.user.company_id.id),
        })

    def _default_outbound_payment_methods(self):
        methods = super(AccountJournal, self)._default_outbound_payment_methods()
        return methods + self.env.ref('account_check_writing.account_payment_method_check_writing')

    @api.model
    def _enable_check_writing_on_bank_journals(self):
        """ Enables check writing payment method and add a check sequence on bank journals.
            Called upon module installation via data file.
        """
        check_writing = self.env.ref('account_check_writing.account_payment_method_check_writing')
        bank_journals = self.search([('type', '=', 'bank')])
        for bank_journal in bank_journals:
            check_sequence = self._create_check_sequence({'name': bank_journal.name, 'company_id': bank_journal.company_id.id})
            bank_journal.write({
                'outbound_payment_method_ids': [(4, check_writing.id, None)],
                'check_sequence_id': check_sequence.id,
            })
