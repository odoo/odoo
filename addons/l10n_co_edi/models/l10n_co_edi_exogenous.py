# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""DIAN Informacion Exogena (Exogenous Information) generation.

Implements annual third-party reporting for DIAN per Resolucion 000124/2021:
- Formato 1001: Payments and withholdings to third parties
- Formato 1003: Withholdings practiced by third parties
- Formato 1005: IVA deductible (purchases)
- Formato 1006: IVA generated (sales)
- Formato 1007: Income received from third parties
"""

from lxml import etree

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# DIAN tax group prefix → exogenous concept code mapping
FORMATO_1001_CONCEPTS = {
    # Payment concepts for Formato 1001
    'honorarios': '5001',
    'comisiones': '5002',
    'servicios': '5003',
    'arrendamientos': '5004',
    'compras': '5005',
    'rendimientos_financieros': '5006',
    'otros_pagos': '5099',
}

# Tax group prefix → DIAN retention code mapping
RETENTION_CODES = {
    'R REN': '06',  # RteFte (income withholding)
    'RTEFTE': '06',
    'R IVA': '05',  # RteIVA (VAT withholding)
    'RTEIVA': '05',
    'R ICA': '07',  # RteICA (municipal withholding)
    'RTEICA': '07',
}

# Tax group prefix → IVA rate extraction
IVA_GROUP_PREFIXES = ['IVA']


class L10nCoEdiExogenousDocument(models.Model):
    _name = 'l10n_co_edi.exogenous.document'
    _description = 'DIAN Exogenous Information Document'
    _order = 'year desc, formato'

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company,
    )
    year = fields.Integer(string='Tax Year', required=True)
    formato = fields.Selection(
        selection=[
            ('1001', 'Formato 1001 - Pagos y Retenciones'),
            ('1003', 'Formato 1003 - Retenciones Practicadas'),
            ('1005', 'Formato 1005 - IVA Deducible'),
            ('1006', 'Formato 1006 - IVA Generado'),
            ('1007', 'Formato 1007 - Ingresos Recibidos'),
        ],
        string='Formato', required=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('sent', 'Sent to DIAN'),
        ],
        string='Status', default='draft', required=True,
    )
    line_ids = fields.One2many(
        'l10n_co_edi.exogenous.document.line', 'document_id',
        string='Detail Lines',
    )
    line_count = fields.Integer(compute='_compute_line_count')
    xml_file = fields.Binary(string='XML File', readonly=True)
    xml_filename = fields.Char(string='XML Filename')
    notes = fields.Text(string='Notes')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for doc in self:
            doc.line_count = len(doc.line_ids)

    def action_compute_lines(self):
        """Aggregate accounting data and populate exogenous document lines."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Can only compute lines for draft documents.'))

        self.line_ids.unlink()

        date_from = fields.Date.to_date(f'{self.year}-01-01')
        date_to = fields.Date.to_date(f'{self.year}-12-31')

        if self.formato == '1001':
            self._compute_formato_1001(date_from, date_to)
        elif self.formato == '1003':
            self._compute_formato_1003(date_from, date_to)
        elif self.formato == '1005':
            self._compute_formato_1005(date_from, date_to)
        elif self.formato == '1006':
            self._compute_formato_1006(date_from, date_to)
        elif self.formato == '1007':
            self._compute_formato_1007(date_from, date_to)

    def _get_posted_move_lines(self, date_from, date_to, move_types=None):
        """Base query for posted move lines in the period."""
        domain = [
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if move_types:
            domain.append(('move_id.move_type', 'in', move_types))
        return self.env['account.move.line'].search(domain)

    def _get_tax_group_prefix(self, tax):
        """Get the normalized tax group name prefix."""
        if not tax or not tax.tax_group_id:
            return ''
        return (tax.tax_group_id.name or '').upper()

    def _compute_formato_1001(self, date_from, date_to):
        """Formato 1001: Payments and withholdings to third parties.

        Aggregates vendor bill lines by partner, including:
        - Total payments made
        - Withholdings applied (RteFte, RteIVA, RteICA)
        """
        move_lines = self._get_posted_move_lines(
            date_from, date_to, ['in_invoice', 'in_refund'],
        )

        # Aggregate by partner
        partner_data = {}
        for line in move_lines:
            partner = line.partner_id or line.move_id.partner_id
            if not partner:
                continue
            pid = partner.commercial_partner_id.id

            if pid not in partner_data:
                partner_data[pid] = {
                    'partner_id': partner.commercial_partner_id.id,
                    'payment_amount': 0.0,
                    'rtefte_base': 0.0, 'rtefte_amount': 0.0,
                    'rteiva_base': 0.0, 'rteiva_amount': 0.0,
                    'rteica_base': 0.0, 'rteica_amount': 0.0,
                }

            if line.tax_line_id:
                prefix = self._get_tax_group_prefix(line.tax_line_id)
                amt = abs(line.balance)
                base = abs(line.tax_base_amount)
                if prefix.startswith(('R REN', 'RTEFTE')):
                    partner_data[pid]['rtefte_amount'] += amt
                    partner_data[pid]['rtefte_base'] += base
                elif prefix.startswith(('R IVA', 'RTEIVA')):
                    partner_data[pid]['rteiva_amount'] += amt
                    partner_data[pid]['rteiva_base'] += base
                elif prefix.startswith(('R ICA', 'RTEICA')):
                    partner_data[pid]['rteica_amount'] += amt
                    partner_data[pid]['rteica_base'] += base
            elif not line.tax_line_id and line.account_id.account_type in (
                'expense', 'expense_direct_cost',
            ):
                partner_data[pid]['payment_amount'] += abs(line.balance)

        self._create_lines_from_data(partner_data, '1001')

    def _compute_formato_1003(self, date_from, date_to):
        """Formato 1003: Withholdings practiced (by customers on our invoices)."""
        move_lines = self._get_posted_move_lines(
            date_from, date_to, ['out_invoice', 'out_refund'],
        )

        partner_data = {}
        for line in move_lines.filtered(lambda l: l.tax_line_id):
            prefix = self._get_tax_group_prefix(line.tax_line_id)
            is_wh = any(prefix.startswith(p) for p in RETENTION_CODES)
            if not is_wh:
                continue

            partner = line.partner_id or line.move_id.partner_id
            if not partner:
                continue
            pid = partner.commercial_partner_id.id

            if pid not in partner_data:
                partner_data[pid] = {
                    'partner_id': partner.commercial_partner_id.id,
                    'base_amount': 0.0,
                    'tax_amount': 0.0,
                }
            partner_data[pid]['tax_amount'] += abs(line.balance)
            partner_data[pid]['base_amount'] += abs(line.tax_base_amount)

        self._create_lines_from_data(partner_data, '1003')

    def _compute_formato_1005(self, date_from, date_to):
        """Formato 1005: IVA deductible (from purchases)."""
        move_lines = self._get_posted_move_lines(
            date_from, date_to, ['in_invoice', 'in_refund'],
        )

        partner_data = {}
        for line in move_lines.filtered(lambda l: l.tax_line_id):
            prefix = self._get_tax_group_prefix(line.tax_line_id)
            if not prefix.startswith('IVA'):
                continue

            partner = line.partner_id or line.move_id.partner_id
            if not partner:
                continue
            pid = partner.commercial_partner_id.id

            if pid not in partner_data:
                partner_data[pid] = {
                    'partner_id': partner.commercial_partner_id.id,
                    'base_amount': 0.0,
                    'tax_amount': 0.0,
                    'tax_rate': abs(line.tax_line_id.amount) if line.tax_line_id.amount_type == 'percent' else 0.0,
                }
            partner_data[pid]['tax_amount'] += abs(line.balance)
            partner_data[pid]['base_amount'] += abs(line.tax_base_amount)

        self._create_lines_from_data(partner_data, '1005')

    def _compute_formato_1006(self, date_from, date_to):
        """Formato 1006: IVA generated (from sales)."""
        move_lines = self._get_posted_move_lines(
            date_from, date_to, ['out_invoice', 'out_refund'],
        )

        partner_data = {}
        for line in move_lines.filtered(lambda l: l.tax_line_id):
            prefix = self._get_tax_group_prefix(line.tax_line_id)
            if not prefix.startswith('IVA'):
                continue

            partner = line.partner_id or line.move_id.partner_id
            if not partner:
                continue
            pid = partner.commercial_partner_id.id

            if pid not in partner_data:
                partner_data[pid] = {
                    'partner_id': partner.commercial_partner_id.id,
                    'base_amount': 0.0,
                    'tax_amount': 0.0,
                    'tax_rate': abs(line.tax_line_id.amount) if line.tax_line_id.amount_type == 'percent' else 0.0,
                }
            partner_data[pid]['tax_amount'] += abs(line.balance)
            partner_data[pid]['base_amount'] += abs(line.tax_base_amount)

        self._create_lines_from_data(partner_data, '1006')

    def _compute_formato_1007(self, date_from, date_to):
        """Formato 1007: Income received from third parties."""
        move_lines = self._get_posted_move_lines(
            date_from, date_to, ['out_invoice', 'out_refund'],
        )

        partner_data = {}
        for line in move_lines.filtered(
            lambda l: not l.tax_line_id and l.account_id.account_type in (
                'income', 'income_other',
            )
        ):
            partner = line.partner_id or line.move_id.partner_id
            if not partner:
                continue
            pid = partner.commercial_partner_id.id

            if pid not in partner_data:
                partner_data[pid] = {
                    'partner_id': partner.commercial_partner_id.id,
                    'base_amount': abs(line.balance),
                    'tax_amount': 0.0,
                }
            else:
                partner_data[pid]['base_amount'] += abs(line.balance)

        self._create_lines_from_data(partner_data, '1007')

    def _create_lines_from_data(self, partner_data, formato):
        """Create exogenous document lines from aggregated partner data."""
        Line = self.env['l10n_co_edi.exogenous.document.line']
        for pid, data in partner_data.items():
            vals = {
                'document_id': self.id,
                'partner_id': data['partner_id'],
                'base_amount': data.get('base_amount', data.get('payment_amount', 0.0)),
                'tax_amount': data.get('tax_amount', 0.0),
                'withholding_amount': (
                    data.get('rtefte_amount', 0.0)
                    + data.get('rteiva_amount', 0.0)
                    + data.get('rteica_amount', 0.0)
                ),
                'tax_rate': data.get('tax_rate', 0.0),
            }
            Line.create(vals)

    def action_confirm(self):
        """Confirm the document and generate XML."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Cannot confirm a document with no lines. Compute lines first.'))
        self.state = 'confirmed'
        self.action_generate_xml()

    def action_generate_xml(self):
        """Generate the DIAN exogenous information XML file."""
        self.ensure_one()
        import base64

        root = self._build_xml()
        xml_bytes = etree.tostring(
            root, pretty_print=True, xml_declaration=True, encoding='UTF-8',
        )
        filename = f'exogena_{self.formato}_{self.year}_{self.company_id.vat or "NIT"}.xml'
        self.xml_file = base64.b64encode(xml_bytes)
        self.xml_filename = filename

    def _build_xml(self):
        """Build the exogenous information XML tree."""
        company = self.company_id
        nit = (company.vat or '').replace('-', '').strip()

        root = etree.Element('mas', xmlns='http://www.dian.gov.co/exogena')
        root.set('version', '2.0')

        # Header: declarant data
        cab = etree.SubElement(root, 'Cab')
        etree.SubElement(cab, 'Ano').text = str(self.year)
        etree.SubElement(cab, 'CodCpt').text = self._get_concepto_code()
        etree.SubElement(cab, 'Formato').text = self.formato
        etree.SubElement(cab, 'Version').text = '10'
        etree.SubElement(cab, 'NumEnvio').text = '1'
        etree.SubElement(cab, 'FecEnvio').text = fields.Date.context_today(self).isoformat()
        etree.SubElement(cab, 'FecInicial').text = f'{self.year}-01-01'
        etree.SubElement(cab, 'FecFinal').text = f'{self.year}-12-31'
        etree.SubElement(cab, 'ValorTotal').text = str(
            sum(l.base_amount for l in self.line_ids)
        )
        etree.SubElement(cab, 'CantReg').text = str(len(self.line_ids))

        # Detail lines
        for line in self.line_ids:
            det = etree.SubElement(root, 'Det')
            partner = line.partner_id
            pvat = (partner.vat or '').replace('-', '').strip()

            etree.SubElement(det, 'TDoc').text = self._get_partner_doc_type(partner)
            etree.SubElement(det, 'NInn').text = pvat
            etree.SubElement(det, 'DV').text = ''
            if partner.is_company:
                etree.SubElement(det, 'ApRaz').text = partner.name or ''
            else:
                names = (partner.name or '').split(' ', 1)
                etree.SubElement(det, 'Ap1').text = names[0] if names else ''
                etree.SubElement(det, 'Nom1').text = names[1] if len(names) > 1 else ''
            etree.SubElement(det, 'Dir').text = partner.street or ''
            etree.SubElement(det, 'CodDpto').text = partner.state_id.code or ''
            etree.SubElement(det, 'CodMun').text = partner.zip or ''
            etree.SubElement(det, 'Pais').text = partner.country_id.code or 'CO'

            # Amounts
            etree.SubElement(det, 'VlrBas').text = f'{line.base_amount:.2f}'
            if line.tax_amount:
                etree.SubElement(det, 'VlrImp').text = f'{line.tax_amount:.2f}'
            if line.withholding_amount:
                etree.SubElement(det, 'VlrRte').text = f'{line.withholding_amount:.2f}'

        return root

    def _get_concepto_code(self):
        """Map formato to DIAN concepto code."""
        return {
            '1001': '1',
            '1003': '3',
            '1005': '5',
            '1006': '6',
            '1007': '7',
        }.get(self.formato, '0')

    def _get_partner_doc_type(self, partner):
        """Map partner identification type to DIAN document type code."""
        if not partner.l10n_latam_identification_type_id:
            return '31'
        code = partner.l10n_latam_identification_type_id.l10n_co_document_code or ''
        if code in ('rut', 'nit'):
            return '31'
        if code in ('national_citizen_id',):
            return '13'
        if code in ('foreign_colombian_card', 'foreign_resident_card'):
            return '22'
        if code == 'passport':
            return '41'
        return '31'

    def action_reset_to_draft(self):
        """Reset document to draft state."""
        self.ensure_one()
        self.state = 'draft'


class L10nCoEdiExogenousDocumentLine(models.Model):
    _name = 'l10n_co_edi.exogenous.document.line'
    _description = 'Exogenous Information Detail Line'
    _order = 'partner_id'

    document_id = fields.Many2one(
        'l10n_co_edi.exogenous.document', required=True, ondelete='cascade',
    )
    partner_id = fields.Many2one('res.partner', string='Third Party', required=True)
    partner_vat = fields.Char(related='partner_id.vat', string='NIT/ID')
    base_amount = fields.Monetary(string='Base Amount', currency_field='currency_id')
    tax_amount = fields.Monetary(string='Tax Amount', currency_field='currency_id')
    withholding_amount = fields.Monetary(string='Withholding Amount', currency_field='currency_id')
    tax_rate = fields.Float(string='Rate (%)')
    currency_id = fields.Many2one(
        'res.currency', related='document_id.company_id.currency_id',
    )
