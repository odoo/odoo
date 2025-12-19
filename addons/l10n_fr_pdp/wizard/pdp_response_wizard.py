from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_repr, float_round, format_list


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
            ("PD", "Paid"),
            ("cancelled", "Cancelled"),
            # For incoming messages
            ("refused", "Refused"),
            ("AP", "Approved"),
            ("in_hand", "In Hand"),
        ],
    )
    available_statuses = fields.Char(
        compute="_compute_available_statuses",
        help="Technical field to enable dynamic selection of status.",
    )
    reason_code = fields.Selection(
        selection=[
            ("TX_TVA_ERR", "Incorrect VAT rate"),
            ("MONTANTTOTAL_ERR", "Incorrect Total Amount"),
            ("CALCUL_ERR", "Billing calculation error"),
            ("NON_CONFORME", "Legal information missing"),
            ("DEST_ERR", "Wrong recipient"),
            ("TRANSAC_INC", "Unknown transaction"),
            ("EMMET_INC", "Unknown sender"),
            ("CONTRAT_TERM", "Contract completed"),
            ("DOUBLE_FACT", "Duplicate Invoice"),
            ("CMD_ERR", "Order number is incorrect or missing"),
            ("ADR_ERR", "Incorrect electronic billing address"),
            ("REF_CT_ABSENT", "Contract reference required to process the missing invoice"),
        ],
    )
    show_reason_code = fields.Boolean(
        compute="_compute_show_reason_code",
        help="Technical field to hide / show the 'Reason Code' in the view.",
    )
    note = fields.Text('Additional note')
    move_count = fields.Integer(
        compute='_compute_move_count',
        store=True,
    )
    fully_paid = fields.Boolean(
        string='Fully paid',
        compute='_compute_paid_amount',
        store=True,
        readonly=False,
    )
    paid_amount = fields.Monetary(
        string='Payment Amount',
        currency_field='currency_id',
        compute='_compute_paid_amount',
        store=True,
        readonly=False,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        compute='_compute_currency_id',
        store=True,
        precompute=True,
        help="The payment's currency.",
    )

    @api.depends('move_ids')
    def _compute_move_count(self):
        for wizard in self:
            wizard.move_count = len(wizard.move_ids)

    @api.depends('move_ids')
    def _compute_currency_id(self):
        eur = self.env['res.currency'].search([('name', '=', 'EUR')], limit=1)
        if not eur:
            raise UserError(self.env._("The EUR currency is missing."))
        self.currency_id = eur

    @api.depends('move_ids')
    def _compute_paid_amount(self):
        for wizard in self:
            move = wizard.move_ids[:1]
            wizard.fully_paid = bool(move) and self._is_fully_paid(move) and not move._pdp_get_paid_lifecycle_total_amount()
            wizard.paid_amount = move.pdp_lifecycle_residual

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
                raise UserError(self.env._("All journal entries must either be purchase or sale documents."))
            category = next(iter(categories))
            if category == 'sale':
                statuses = ['PD', 'cancelled']
            else:
                statuses = ['refused', 'AP']
            wizard.available_statuses = ','.join(statuses)

    @api.model
    def _get_base_lines(self, move):
        move.ensure_one()
        company = move.company_id

        base_amls = move.line_ids.filtered(lambda x: x.display_type == 'product')
        base_lines = [move._prepare_product_base_line_for_taxes_computation(aml) for aml in base_amls]
        epd_amls = move.line_ids.filtered(lambda line: line.display_type == 'epd')
        base_lines += [move._prepare_epd_base_line_for_taxes_computation(line) for line in epd_amls]
        cash_rounding_amls = move.line_ids \
            .filtered(lambda line: line.display_type == 'rounding' and not line.tax_repartition_line_id)
        base_lines += [move._prepare_cash_rounding_base_line_for_taxes_computation(line) for line in cash_rounding_amls]
        tax_amls = move.line_ids.filtered('tax_repartition_line_id')
        tax_lines = [move._prepare_tax_line_for_taxes_computation(x) for x in tax_amls]

        AccountTax = self.env['account.tax']
        AccountTax._add_tax_details_in_base_lines(base_lines, company)
        AccountTax._round_base_lines_tax_details(base_lines, company, tax_lines=tax_lines)

        return base_lines

    @api.model
    def _get_tax_details(self, base_lines):

        def tax_details_grouping_function(base_line, tax_data):
            if not tax_data:
                return None
            tax = tax_data['tax']
            return {
                'amount': tax.amount,
            }

        # Tax details
        AccountTax = self.env['account.tax']
        base_lines_aggregated_values_for_tax_details = AccountTax._aggregate_base_lines_tax_details(base_lines, tax_details_grouping_function)
        return AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values_for_tax_details)

    @api.model
    def _get_early_payment_discount_tax_details(self, base_lines):

        def tax_details_grouping_function(base_line, tax_data):
            if not tax_data or base_line['special_type'] != 'early_payment':
                return None

            tax = tax_data['tax']
            return {
                'amount': tax.amount,
            }

        # Tax details
        AccountTax = self.env['account.tax']
        base_lines_aggregated_values_for_tax_details = AccountTax._aggregate_base_lines_tax_details(base_lines, tax_details_grouping_function)
        return AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values_for_tax_details)

    @api.model
    def _get_payments_data_fully_paid(self, move):
        move.ensure_one()
        base_lines = self._get_base_lines(move)

        full_tax_details = self._get_tax_details(base_lines)
        epd_tax_details = self._get_early_payment_discount_tax_details(base_lines)

        collected = [
            {
                "amount_changed": False,
                "type_code": "MEN",
                "amount": self._round_format_number_2(-move.direction_sign * (tax_details['base_amount'] + tax_details['tax_amount'])),
                "currency": "EUR",
                "tax_percent": self._round_format_number_2(key['amount']),
            } for key, tax_details in full_tax_details.items() if key
        ]

        discounted = [
            {
                "amount_changed": False,
                "type_code": "ESC",
                "amount": self._round_format_number_2(move.direction_sign * (tax_details['base_amount'] + tax_details['tax_amount'])),
                "currency": "EUR",
                "tax_percent": self._round_format_number_2(key['amount']),
            } for key, tax_details in epd_tax_details.items() if key
        ]

        return collected + discounted

    @api.model
    def _get_payments_data(self, move, forced_amount=None):
        move.ensure_one()

        if not forced_amount and self._is_fully_paid(move) and not move._pdp_get_paid_lifecycle_total_amount():
            return self._get_payments_data_fully_paid(move)

        collected_amount = forced_amount or move.pdp_lifecycle_residual
        collected_sign = -1 if collected_amount < 0 else 1

        base_lines = self._get_base_lines(move)
        tax_details = self._get_tax_details(base_lines)

        to_pay = {
            key['amount']: move.direction_sign * (tax_details['base_amount'] + tax_details['tax_amount'])
            for key, tax_details in tax_details.items()
        }
        collected_amounts = {}
        collected_amount_residual = abs(collected_amount)
        for tax_percent, amount in to_pay.items():
            available = min(collected_amount_residual, abs(amount))
            collected_amounts[tax_percent] = collected_sign * available
            collected_amount_residual -= abs(available)
            if move.currency_id.is_zero(collected_amount_residual):
                break

        return [
            {
                "amount_changed": False,
                "type_code": "MEN",
                "amount": self._round_format_number_2(amount),
                "currency": "EUR",
                "tax_percent": self._round_format_number_2(tax_percent),
            }
            for tax_percent, amount in collected_amounts.items()
        ]

    @api.model
    def _round_format_number_2(self, number):
        # Round and format as number with 2 precision digits
        if number is None:
            return None
        rounded = float_round(number, precision_digits=2)
        return float_repr(rounded, precision_digits=2)

    @api.model
    def _is_fully_paid(self, move):
        move.ensure_one()
        if move.payment_state != 'paid':
            return False

        return move.company_currency_id.compare_amounts(abs(move._pdp_get_paid_amount()), abs(move.amount_total_signed)) >= 0.0

    def button_send(self):
        self.ensure_one()

        if not self.status:
            raise UserError(self.env._("Please select a Status."))
        # Note: `_compute_available_statuses` ensures that all moves are either sale or puchase documents

        if (unsent_moves := self.move_ids.filtered(lambda m: not m.pdp_is_sent)):
            raise UserError(self.env._("Some of the journal entries were not sent to the Approved Platform yet: %s", format_list(self.env, unsent_moves.mapped('display_name'))))

        if self.status == 'refused' and not self.reason_code:
            raise UserError(self.env._("To refuse an invoice please select a Reason Code."))
        if self.status == 'refused' and not self.note:
            raise UserError(self.env._("To refuse an invoice please enter a Note."))
        if self.status in ('cancelled', 'refused') and (not_cancelled_moves := self.move_ids.filtered(lambda m: m.state != 'cancel')):
            raise UserError(self.env._("Some of the journal entries are not cancelled: %s", format_list(self.env, not_cancelled_moves.mapped('display_name'))))
        if self.status == 'AP' and (not_approved_moves := self.move_ids.filtered(lambda m: m.state != 'posted')):
            raise UserError(self.env._("Some of the journal entries are not posted: %s", format_list(self.env, not_approved_moves.mapped('display_name'))))
        forced_amount = None
        if (
            self.status == 'PD'
            and self.move_count == 1
            and not self.fully_paid
            and self.currency_id.compare_amounts(self.paid_amount, self.move_ids[:1].amount_total) < 0.0
        ):
            forced_amount = self.paid_amount

        if self.status == 'PD' and any(move.currency_id.name != 'EUR' for move in self.move_ids):
            raise UserError(self.env._("Only journal entries in currency EUR are supported."))

        if self.status == 'PD' and (untaxed_moves := self.move_ids.filtered(lambda m: not m.amount_tax)):
            raise UserError(self.env._("Some of the journal entries are without tax: %s", format_list(self.env, untaxed_moves.mapped('display_name'))))
        if self.status == 'PD' and not forced_amount and (up_to_date_moves := self.move_ids.filtered(lambda m: not m.pdp_lifecycle_residual)):
            raise UserError(self.env._("Some of the journal entries have no payments to send: %s", format_list(self.env, up_to_date_moves.mapped('display_name'))))

        base_info = {
            field: value for field in ['note', 'reason_code'] if (value := self[field])
        }

        moves_by_company = self.move_ids.grouped('company_id')
        for company, moves in moves_by_company.items():
            if self.status == 'PD':
                additional_info = {
                    move.peppol_message_uuid: {
                        **base_info,
                        'payments': self._get_payments_data(move, forced_amount=forced_amount),
                    }
                    for move in moves
                }
            else:
                additional_info = {move.peppol_message_uuid: base_info for move in moves}
            company.account_peppol_edi_user._pdp_send_response(moves, self.status, additional_info=additional_info)
        return self.env.context.get('cancel_res', True)
