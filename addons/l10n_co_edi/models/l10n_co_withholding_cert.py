# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nCoWithholdingCertificate(models.Model):
    _name = 'l10n_co.withholding.certificate'
    _description = 'Colombian Withholding Certificate'
    _order = 'date_to desc, partner_id'
    _rec_name = 'display_name'

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Supplier/Recipient', required=True,
        help='Partner to whom the certificate is issued.',
    )
    date_from = fields.Date(string='Period Start', required=True)
    date_to = fields.Date(string='Period End', required=True)
    certificate_type = fields.Selection(
        selection=[
            ('rtefte', 'RteFte (Income Withholding)'),
            ('rteiva', 'RteIVA (VAT Withholding)'),
            ('rteica', 'RteICA (Municipal Withholding)'),
            ('all', 'All Withholdings'),
        ],
        string='Type',
        default='all',
        required=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('delivered', 'Delivered'),
        ],
        default='draft',
        tracking=True,
    )
    line_ids = fields.One2many(
        'l10n_co.withholding.certificate.line', 'certificate_id',
        string='Certificate Lines',
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id',
    )
    total_base = fields.Monetary(
        string='Total Base', compute='_compute_totals', store=True,
    )
    total_withheld = fields.Monetary(
        string='Total Withheld', compute='_compute_totals', store=True,
    )
    delivery_date = fields.Date(string='Delivery Date')
    notes = fields.Text()

    display_name = fields.Char(compute='_compute_display_name')

    @api.depends('partner_id', 'date_from', 'date_to', 'certificate_type')
    def _compute_display_name(self):
        for rec in self:
            partner_name = rec.partner_id.name or ''
            type_label = dict(rec._fields['certificate_type'].selection).get(
                rec.certificate_type, ''
            )
            date_str = ''
            if rec.date_from and rec.date_to:
                date_str = f' ({rec.date_from} — {rec.date_to})'
            rec.display_name = f'{partner_name} — {type_label}{date_str}'

    @api.depends('line_ids.base_amount', 'line_ids.withheld_amount')
    def _compute_totals(self):
        for cert in self:
            cert.total_base = sum(cert.line_ids.mapped('base_amount'))
            cert.total_withheld = sum(cert.line_ids.mapped('withheld_amount'))

    def action_confirm(self):
        for cert in self:
            if not cert.line_ids:
                raise UserError(_(
                    'Cannot confirm certificate for %s: no withholding lines.',
                    cert.partner_id.name,
                ))
            cert.state = 'confirmed'

    def action_deliver(self):
        for cert in self:
            cert.state = 'delivered'
            cert.delivery_date = fields.Date.today()

    def action_reset_draft(self):
        for cert in self:
            cert.state = 'draft'
            cert.delivery_date = False

    def action_compute_lines(self):
        """Compute withholding certificate lines from journal entries."""
        for cert in self:
            cert.line_ids.unlink()
            lines_data = cert._get_withholding_data()
            for vals in lines_data:
                vals['certificate_id'] = cert.id
                self.env['l10n_co.withholding.certificate.line'].create(vals)

    def _get_withholding_data(self):
        """Aggregate withholding data from account.move.line for the period.

        Groups by tax to produce one line per tax in the period.
        """
        self.ensure_one()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('partner_id', '=', self.partner_id.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('tax_line_id', '!=', False),
        ]

        # Filter by withholding tax group names based on certificate type
        group_prefixes = self._get_group_prefixes()

        move_lines = self.env['account.move.line'].search(domain)
        result = {}

        for ml in move_lines:
            tax = ml.tax_line_id
            group_name = (tax.tax_group_id.name or '').upper()
            if not any(group_name.startswith(p) for p in group_prefixes):
                continue

            key = tax.id
            if key not in result:
                result[key] = {
                    'tax_id': tax.id,
                    'concept': tax.name,
                    'rate': abs(tax.amount),
                    'base_amount': 0.0,
                    'withheld_amount': 0.0,
                }

            result[key]['withheld_amount'] += abs(ml.balance)

            # Find the corresponding base line(s) in the same move
            base_lines = ml.move_id.line_ids.filtered(
                lambda l: (
                    l.tax_ids & tax
                    and not l.tax_line_id
                    and l.partner_id == ml.partner_id
                )
            )
            if base_lines:
                result[key]['base_amount'] += sum(abs(bl.balance) for bl in base_lines)

        return list(result.values())

    def _get_group_prefixes(self):
        """Return tax group name prefixes for the selected certificate type."""
        mapping = {
            'rtefte': ['R REN', 'RTEFTE'],
            'rteiva': ['R IVA', 'RTEIVA'],
            'rteica': ['R ICA', 'RTEICA'],
            'all': ['R REN', 'RTEFTE', 'R IVA', 'RTEIVA', 'R ICA', 'RTEICA'],
        }
        return mapping.get(self.certificate_type, mapping['all'])


class L10nCoWithholdingCertificateLine(models.Model):
    _name = 'l10n_co.withholding.certificate.line'
    _description = 'Withholding Certificate Line'
    _order = 'concept'

    certificate_id = fields.Many2one(
        'l10n_co.withholding.certificate', required=True, ondelete='cascade',
    )
    currency_id = fields.Many2one(
        'res.currency', related='certificate_id.currency_id',
    )
    tax_id = fields.Many2one('account.tax', string='Tax')
    concept = fields.Char(string='Concept', required=True)
    rate = fields.Float(string='Rate (%)', digits=(5, 2))
    base_amount = fields.Monetary(string='Base Amount')
    withheld_amount = fields.Monetary(string='Withheld Amount')
