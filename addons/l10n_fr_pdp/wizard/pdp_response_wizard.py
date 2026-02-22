from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_list


SALE_STATUSES = {'paid', 'cancelled'}


class PdpResponseWizard(models.TransientModel):
    _name = 'pdp.response.wizard'
    _description = "PDP Response wizard"

    move_ids = fields.Many2many(
        comodel_name='account.move',
        required=True,
    )
    status = fields.Selection(
        selection=[
            # For outgoing messages
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
            # For incoming messages
            ("refused", "Refused"),
            # TODO: maybe we should not support the following
            ("approved", "Approved"),
            # ("contested", "Contested"),
            # ("payment_sent", "Payment Sent"),
        ],
    )
    available_statuses = fields.Char(
        compute="_compute_available_statuses",
        help="Technical field to enable dynamic selection of status.",
    )
    reason_code = fields.Selection(
        selection=[
            ("TX_TVA_ERR", " Taux de TVA erroné"),
            ("MONTANTTOTAL_ERR", "Montant Total Erroné"),
            ("CALCUL_ERR", "Erreur de calcul de la facture"),
            ("NON_CONFORME", "Facture en doublon (déjà émise / réçue)"),
            ("DEST_ERR", "Erreur de destinataire"),
            ("TRANSAC_INC", "Transaction inconnue"),
            ("EMMET_INC", "Emetteur inconnu"),
            ("CONTRAT_TERM", "Contrat terminé"),
            ("DOUBLE_FACT", "DOUBLE FACTURE"),
            ("CMD_ERR", "N° de COMMANDE Incorrect ou manquant"),
            ("ADR_ERR", "L'adresse de facturation électronique erronée"),
            ("REF_CT_ABSENT", "Référence contractuelle nécessaire pour le traitement de la facture manquante"),
        ],
    )
    show_reason_code = fields.Boolean(compute="_compute_show_reason_code", help="Technical field to hide / show the 'Reason Code' in the view.")
    note = fields.Text('Additional note')

    @api.depends('status')
    def _compute_show_reason_code(self):
        for wizard in self:
            wizard.show_reason_code = wizard.status == 'refused'

    @api.depends('move_ids')
    def _compute_available_statuses(self):
        move_type_map = {
            **{move_type: 'sale' for move_type in self.env['account.move'].get_sale_types(include_receipts=True)},
            **{move_type: 'purchase' for move_type in self.env['account.move'].get_purchase_types(include_receipts=True)},
        }
        for wizard in self:
            categories = set(self.move_ids.mapped(lambda m: move_type_map.get(m.move_type)))
            if len(categories) != 1 or categories - {'sale', 'purchase'}:
                raise UserError("All journal entries must either be purchase or sale documents.")
            category = next(iter(categories))
            if category == 'sale':
                statuses = ['paid', 'cancelled']
            else:
                statuses = ['refused', 'approved', 'contested', 'payment_sent']
            wizard.available_statuses = ','.join(statuses)

    def button_send(self):
        self.ensure_one()

        if not self.status:
            raise UserError(_("Please select a Status."))
        # Note: `_compute_available_statuses` ensures that all moves are either sale or puchase documents

        if self.status == 'refused' and not self.reason_code:
            raise UserError(_("To refuse an invoice please select a Reason Code."))
        if self.status == 'paid' and (not_paid_moves := self.move_ids.filtered(lambda m: m.payment_state != 'paid')):
            raise UserError(_("Some of the moves are not (fully) paid: %s", format_list(self.env, not_paid_moves.mapped('display_name'))))
        if self.status in ('cancelled', 'refused') and (not_cancelled_moves := self.move_ids.filtered(lambda m: m.state != 'cancel')):
            raise UserError(_("Some of the moves are not cancelled: %s", format_list(self.env, not_cancelled_moves.mapped('display_name'))))
        if self.status == 'approved' and (not_approved_moves := self.move_ids.filtered(lambda m: m.state != 'posted')):
            raise UserError(_("Some of the moves are not posted: %s", format_list(self.env, not_approved_moves.mapped('display_name'))))

        additional_info = {
            'details': {
                field: value for field in ['note', 'reason_code'] if (value := self[field])
            }
        }

        moves_by_company = self.move_ids.grouped('company_id')
        for company, moves in moves_by_company.items():
            if self.status == 'paid':
                for move in moves:
                    # TODO: full amount, split per VAT
                    payments = []
                    # TODO: allow note?
                    company.pdp_edi_user._pdp_send_response(moves, 'paid', {'payments': payments})
            else:
                company.pdp_edi_user._pdp_send_response(moves, self.status, additional_info=additional_info)
        return self.env.context.get('cancel_res', True)
