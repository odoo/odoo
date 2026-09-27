# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, ValidationError
from odoo.fields import Domain

try:
    from cn2an import an2cn
except ImportError:
    an2cn = None


class AccountMove(models.Model):
    _inherit = 'account.move'

    fapiao = fields.Char(string='Fapiao Number', copy=False, tracking=True)
    l10n_cn_differential_taxation_method = fields.Selection(
        selection=[
            ('01', 'Full Amount Fapiao'),
            ('02', 'Net Amount Fapiao'),
        ],
        string="VAT Differential Taxation Method",
    )
    l10n_cn_output_vat_offset_origin_id = fields.Many2one(
        string="Output VAT Offset Origin Entry",
        comodel_name='account.move',
        ondelete='restrict',
        copy=False,
    )
    l10n_cn_output_vat_offset_origin_line_ids = fields.One2many(
        string="Output VAT Offset Origin Lines",
        comodel_name='account.move.line',
        inverse_name='l10n_cn_output_vat_offset_move_id',
    )
    l10n_cn_output_vat_offset_move_ids = fields.One2many(
        string="Output VAT Offset Entries",
        comodel_name='account.move',
        inverse_name='l10n_cn_output_vat_offset_origin_id',
    )
    l10n_cn_vat_differential_taxation = fields.Boolean(
        related='company_id.l10n_cn_vat_differential_taxation',
    )

    @api.constrains('fapiao')
    def _check_fapiao(self):
        for record in self:
            if record.fapiao and not record.fapiao.isdecimal():
                raise ValidationError(_("Please enter a correct fapiao number."))

    @api.model
    def check_cn2an(self):
        return an2cn

    @api.model
    def _convert_to_amount_in_word(self, number):
        """Convert number to ``amount in words`` for Chinese financial usage."""
        if not self.check_cn2an():
            return None
        return an2cn(number, 'rmb')

    def _count_attachments(self):
        domains = [[('res_model', '=', 'account.move'), ('res_id', '=', self.id)]]
        statement_ids = self.line_ids.mapped('statement_id')
        payment_ids = self.line_ids.mapped('payment_id')
        if statement_ids:
            domains.append([('res_model', '=', 'account.bank.statement'), ('res_id', 'in', statement_ids.ids)])
        if payment_ids:
            domains.append([('res_model', '=', 'account.payment'), ('res_id', 'in', payment_ids.ids)])
        return self.env['ir.attachment'].search_count(Domain.OR(domains))

    def _check_l10n_cn_balance_deduction_info(self):
        """Ensure each product line has exactly one percentage tax and required balance deduction details.

        China's difference taxation requires a single percentage-based tax
        per line to accurately compute net taxable amounts and VAT. Non-zero tax lines
        must specify balance deduction info unless full-amount taxation (method '01') applies.
        """
        for move in self:
            for line in move.invoice_line_ids.filtered(lambda line: line.display_type == 'product'):
                tax = line.tax_ids
                if len(tax) != 1 or tax.amount_type != 'percent':
                    raise ValidationError(self.env._(
                        "Each invoice line must have one and only one tax "
                        "with a percentage computation type.",
                    ))

                if not tax.amount:
                    continue

                if not line.l10n_cn_balance_deduction_ids:
                    if move.l10n_cn_differential_taxation_method == '01':
                        continue

                    raise ValidationError(self.env._(
                        "Please provide Balance Deduction Information for "
                        "all applicable invoice lines before confirming the invoice.",
                    ))

    def _create_l10n_cn_output_vat_offset_moves(self):
        """Create and post Output VAT Offset Entries for the given credit notes."""
        companies = self.mapped('company_id')

        for company in companies:
            journal = company.l10n_cn_output_vat_offset_journal_id

            if not journal.active:
                raise ValidationError(self.env._(
                    "No active 'Output VAT Offset Journal' is configured. "
                    "Please select an active journal in the settings before "
                    "confirming the invoice.",
                ))

        offset_move_data = []

        for move in self:
            lines = move.invoice_line_ids.filtered(
                'l10n_cn_balance_deduction_ids',
            )

            # For method '01', create a separate offset entry for each line;
            # otherwise, create a single offset entry for all applicable lines.
            if move.l10n_cn_differential_taxation_method == '01':
                for line in lines:
                    if vals := line._prepare_l10n_cn_output_vat_offset_move_vals():
                        offset_move_data.append(vals)
            else:
                if vals := lines._prepare_l10n_cn_output_vat_offset_move_vals():
                    offset_move_data.append(vals)

        if not offset_move_data:
            return

        # Create all offset moves in a single batch.
        offset_moves = self.env['account.move'].create(offset_move_data)

        offset_moves.action_post()

    def _post(self, soft=True):
        """Validate balance deduction info and create Output VAT offset moves for Chinese differential taxation invoices upon posting."""
        cn_moves = self.filtered(
            lambda move: (
                move.country_code == 'CN'
                and move.l10n_cn_differential_taxation_method
                and move.l10n_cn_vat_differential_taxation
            ),
        )

        if not cn_moves:
            return super()._post(soft=soft)

        cn_moves._check_l10n_cn_balance_deduction_info()

        res = super()._post(soft=soft)

        cn_moves.filtered(
            lambda move: move.state == 'posted',
        )._create_l10n_cn_output_vat_offset_moves()

        return res

    def _prepare_l10n_cn_output_vat_offset_line_vals(self, name, account_id, balance):
        """Prepare account move line values for an Output VAT offset journal entry."""
        self.ensure_one()

        return {
            'name': name,
            'partner_id': self.partner_id.id,
            'account_id': account_id.id,
            'balance': balance,
            'date': self.date,
            'currency_id': self.currency_id.id,
            'is_storno': self.is_storno,
        }

    def _check_l10n_cn_output_vat_offset_direct_modification(self):
        for move in self:
            if move.l10n_cn_output_vat_offset_origin_id:
                raise RedirectWarning(
                    message=self.env._(
                        "To ensure data synchronization between Balance Deduction Information and accounting records, "
                        "please make modifications from Balance Deduction Information.",
                    ),
                    action=move.l10n_cn_output_vat_offset_origin_id._get_records_action(),
                    button_text=self.env._("Original Invoice"),
                )

    def _reverse_l10n_cn_output_vat_offset_moves(self):
        self._check_l10n_cn_output_vat_offset_direct_modification()

        offset_moves = self.invoice_line_ids.l10n_cn_output_vat_offset_move_id

        if not offset_moves:
            return

        default_values_list = [
            {
                'ref': self.env._("Reversal of: %s", offset_move.name),
                'l10n_cn_output_vat_offset_origin_id': offset_move.l10n_cn_output_vat_offset_origin_id.id,
            }
            for offset_move in offset_moves
        ]
        offset_moves._reverse_moves(
            default_values_list=default_values_list,
            cancel=True,
        )
        self.invoice_line_ids.l10n_cn_output_vat_offset_move_id = False

    def button_draft(self):
        cn_moves = self.filtered(lambda move: move.country_code == 'CN' and move.l10n_cn_vat_differential_taxation)

        if cn_moves:
            cn_moves._reverse_l10n_cn_output_vat_offset_moves()

        return super().button_draft()

    def action_open_l10n_cn_output_vat_offset_entries(self):
        self.ensure_one()

        return self.l10n_cn_output_vat_offset_move_ids._get_records_action(
            name=self.env._("Output VAT Offset Entries"),
        )
