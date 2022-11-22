import uuid
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_sa_reversal_reason = fields.Char("Reversal Reason", help="Reason for which the original invoice was reversed")

    l10n_sa_uuid = fields.Char(string='Document UUID', copy=False, help="Universally unique identifier of the Invoice")
    l10n_sa_pos_origin = fields.Boolean("POS Origin", default=False, copy=False,
                                        help="Whether or not the invoice originates from a POS order")

    def _l10n_sa_get_previous_invoice(self):
        """
            Search for the previous invoice relating to the current record. We use the l10n_sa_confirmation_datetime
            field to figure out which invoice comes before which.
        :return: Previous invoice record
        :rtype: recordset
        """
        self.ensure_one()
        return self.search(
            [('move_type', 'in', self.get_invoice_types()), ('id', '!=', self.id), ('state', '=', 'posted'),
             ('l10n_sa_confirmation_datetime', '<', self.l10n_sa_confirmation_datetime)], limit=1,
            order='l10n_sa_confirmation_datetime desc')

    @api.model_create_multi
    def create(self, vals_list):
        """
            Override to add a UUID on the invoice whenever it is created
        """
        for vals in vals_list:
            if 'l10n_sa_uuid' not in vals:
                vals['l10n_sa_uuid'] = uuid.uuid1()
        return super(AccountMove, self).create(vals_list)

    def button_cancel_posted_moves(self):
        """
            Override to prohibit the cancellation of invoices submitted to ZATCA
        """
        for move in self:
            if move.edi_document_ids.filtered(lambda doc: doc.edi_format_id.code == "sa_zatca"):
                raise UserError(_("Cannot cancel eInvoices submitted to ZATCA. Please, issue a Credit Note instead"))
        return super(AccountMove, self).button_cancel_posted_moves()
