# Part of GPCB. See LICENSE file for full copyright and licensing details.

import base64
import logging

from lxml import etree

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Colombian labor law constants (2026)
SMMLV_2026 = 1_423_500  # Salario Minimo Mensual Legal Vigente
TRANSPORT_SUBSIDY_2026 = 200_000  # Auxilio de Transporte
SMMLV_THRESHOLD_TRANSPORT = 2  # Transport subsidy for <= 2 SMMLV


class L10nCoPayrollDocument(models.Model):
    _name = 'l10n_co.payroll.document'
    _description = 'Electronic Payroll Document (Nomina Electronica)'
    _order = 'period_start desc, employee_id'
    _inherit = ['mail.thread']

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company,
    )
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_vat = fields.Char(related='employee_id.identification_id', string='ID Number')

    # Period
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    settlement_date = fields.Date(string='Payment Date', required=True)
    document_number = fields.Char(string='Document Number', readonly=True, copy=False)

    # Document type
    document_type = fields.Selection(
        selection=[
            ('nomina', 'Nomina Individual'),
            ('ajuste', 'Nomina Individual de Ajuste'),
            ('nota', 'Nota de Ajuste (Reversal)'),
        ],
        string='Document Type', default='nomina', required=True,
    )
    adjusted_document_id = fields.Many2one(
        'l10n_co.payroll.document', string='Adjusted Document',
        help='Original document being adjusted (for ajuste/nota types).',
    )

    # State
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('sent', 'Sent to DIAN'),
            ('validated', 'Validated by DIAN'),
            ('rejected', 'Rejected by DIAN'),
        ],
        string='Status', default='draft', required=True, tracking=True,
    )

    # Lines
    earning_ids = fields.One2many(
        'l10n_co.payroll.document.line', 'document_id',
        domain=[('line_type', '=', 'earning')], string='Earnings',
    )
    deduction_ids = fields.One2many(
        'l10n_co.payroll.document.line', 'document_id',
        domain=[('line_type', '=', 'deduction')], string='Deductions',
    )
    provision_ids = fields.One2many(
        'l10n_co.payroll.document.line', 'document_id',
        domain=[('line_type', '=', 'provision')], string='Provisions',
    )

    # Totals
    total_earnings = fields.Monetary(
        compute='_compute_totals', store=True, string='Total Earnings',
        currency_field='currency_id',
    )
    total_deductions = fields.Monetary(
        compute='_compute_totals', store=True, string='Total Deductions',
        currency_field='currency_id',
    )
    total_provisions = fields.Monetary(
        compute='_compute_totals', store=True, string='Total Provisions',
        currency_field='currency_id',
    )
    net_pay = fields.Monetary(
        compute='_compute_totals', store=True, string='Net Pay',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id',
    )

    # CUNE
    cune = fields.Char(string='CUNE', readonly=True, copy=False)

    # DIAN
    xml_file = fields.Binary(string='XML File', readonly=True)
    xml_filename = fields.Char(string='XML Filename')
    dian_response = fields.Text(string='DIAN Response')
    dian_response_status = fields.Char(string='DIAN Status Code')

    # Accounting
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)

    @api.depends(
        'earning_ids.amount', 'deduction_ids.amount', 'provision_ids.amount',
    )
    def _compute_totals(self):
        for doc in self:
            doc.total_earnings = sum(doc.earning_ids.mapped('amount'))
            doc.total_deductions = sum(doc.deduction_ids.mapped('amount'))
            doc.total_provisions = sum(doc.provision_ids.mapped('amount'))
            doc.net_pay = doc.total_earnings - doc.total_deductions

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_confirm(self):
        """Confirm the document and generate CUNE."""
        self.ensure_one()
        if not self.earning_ids:
            raise UserError(_('Cannot confirm a payroll document with no earning lines.'))
        if not self.document_number:
            self.document_number = self.env['ir.sequence'].next_by_code(
                'l10n_co.payroll.document'
            ) or _('New')
        self._compute_cune()
        self.state = 'confirmed'

    def action_generate_xml(self):
        """Generate the DIAN payroll UBL XML."""
        self.ensure_one()
        root = self._build_payroll_xml()
        xml_bytes = etree.tostring(
            root, pretty_print=True, xml_declaration=True, encoding='UTF-8',
        )
        filename = f'ne_{self.document_number or self.id}_{self.employee_id.identification_id or "EMP"}.xml'
        self.xml_file = base64.b64encode(xml_bytes)
        self.xml_filename = filename

    def action_send_to_dian(self):
        """Submit the payroll document to DIAN."""
        self.ensure_one()
        if not self.xml_file:
            self.action_generate_xml()

        # Use the DIAN client from l10n_co_edi
        try:
            dian_client = self.env['l10n_co_edi.dian.client']
            company = self.company_id
            xml_content = base64.b64decode(self.xml_file)

            response = dian_client._send_bill_sync(
                company, self.xml_filename, xml_content,
            )

            if response and dian_client._is_dian_response_success(response):
                self.state = 'validated'
                self.dian_response = response.get('application_response', '')
                self.dian_response_status = str(response.get('status_code', ''))
            elif response:
                self.state = 'rejected'
                self.dian_response = response.get('raw_response', '')
                self.dian_response_status = str(response.get('status_code', ''))
            else:
                self.state = 'sent'
                self.dian_response = 'Submission pending — no response received.'

        except Exception as e:
            _logger.exception('Payroll DIAN submission failed for %s', self.document_number)
            self.dian_response = str(e)
            self.state = 'sent'

    def action_create_accounting_entry(self):
        """Create a journal entry from the confirmed payroll document."""
        self.ensure_one()
        if self.move_id:
            raise UserError(_('An accounting entry already exists for this document.'))
        if self.state not in ('confirmed', 'sent', 'validated'):
            raise UserError(_('Document must be confirmed before creating an accounting entry.'))

        move_lines = self._build_journal_entry_lines()
        if not move_lines:
            raise UserError(_('No accounting lines could be generated.'))

        journal = self.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', self.company_id.id)],
            limit=1,
        )
        if not journal:
            raise UserError(_('No general journal found for accounting entries.'))

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': self.settlement_date,
            'ref': f'Nómina {self.document_number} — {self.employee_id.name}',
            'line_ids': move_lines,
        })
        self.move_id = move.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
        }

    def _build_journal_entry_lines(self):
        """Build journal entry lines from payroll earnings and deductions."""
        lines = []
        # Earnings → Expense accounts (debit)
        for earning in self.earning_ids:
            account = earning.account_id
            if not account:
                continue
            lines.append((0, 0, {
                'name': f'{earning.concept} — {self.employee_id.name}',
                'account_id': account.id,
                'debit': earning.amount,
                'credit': 0,
            }))

        # Deductions → Liability accounts (credit)
        for deduction in self.deduction_ids:
            account = deduction.account_id
            if not account:
                continue
            lines.append((0, 0, {
                'name': f'{deduction.concept} — {self.employee_id.name}',
                'account_id': account.id,
                'debit': 0,
                'credit': deduction.amount,
            }))

        # Net pay → Payable account (credit)
        if self.net_pay > 0:
            payable_account = self.env['account.account'].search([
                ('account_type', '=', 'liability_payable'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            if payable_account:
                lines.append((0, 0, {
                    'name': f'Net pay — {self.employee_id.name}',
                    'account_id': payable_account.id,
                    'debit': 0,
                    'credit': self.net_pay,
                }))

        return lines

    def action_reset_to_draft(self):
        self.ensure_one()
        self.state = 'draft'

    # ------------------------------------------------------------------
    # CUNE
    # ------------------------------------------------------------------

    def _compute_cune(self):
        """Compute the CUNE (Codigo Unico de Nomina Electronica)."""
        cune_model = self.env['l10n_co.payroll.cune']
        for doc in self:
            doc.cune = cune_model._compute_cune(doc)

    # ------------------------------------------------------------------
    # XML Generation
    # ------------------------------------------------------------------

    def _build_payroll_xml(self):
        """Build UBL 2.1 payroll XML for DIAN."""
        ns = 'urn:dian:gov:co:facturaelectronica:NominaIndividual'
        root = etree.Element('NominaIndividual', xmlns=ns)
        root.set('SchemaLocation', ns)

        company = self.company_id
        employee = self.employee_id
        nit = (company.vat or '').replace('-', '').strip()
        emp_id = (employee.identification_id or '').replace('-', '').strip()

        # Header
        etree.SubElement(root, 'TipoNota').text = {
            'nomina': '102',
            'ajuste': '103',
            'nota': '104',
        }.get(self.document_type, '102')
        etree.SubElement(root, 'CUNE').text = self.cune or ''
        etree.SubElement(root, 'Numero').text = self.document_number or ''
        etree.SubElement(root, 'FechaGen').text = fields.Date.context_today(self).isoformat()
        etree.SubElement(root, 'FechaPagoInicio').text = str(self.period_start)
        etree.SubElement(root, 'FechaPagoFin').text = str(self.period_end)
        etree.SubElement(root, 'FechaPago').text = str(self.settlement_date)

        # Employer
        emp_node = etree.SubElement(root, 'Empleador')
        etree.SubElement(emp_node, 'NIT').text = nit
        etree.SubElement(emp_node, 'RazonSocial').text = company.name
        etree.SubElement(emp_node, 'Direccion').text = company.street or ''
        etree.SubElement(emp_node, 'Municipio').text = company.zip or ''

        # Worker
        worker_node = etree.SubElement(root, 'Trabajador')
        etree.SubElement(worker_node, 'TipoDocumento').text = '13'  # CC default
        etree.SubElement(worker_node, 'NumeroDocumento').text = emp_id
        names = (employee.name or '').split(' ', 1)
        etree.SubElement(worker_node, 'PrimerApellido').text = names[0] if names else ''
        etree.SubElement(worker_node, 'PrimerNombre').text = names[1] if len(names) > 1 else ''

        # Earnings
        dev = etree.SubElement(root, 'Devengados')
        for earning in self.earning_ids:
            item = etree.SubElement(dev, 'Concepto')
            etree.SubElement(item, 'Tipo').text = earning.concept_code or ''
            etree.SubElement(item, 'Descripcion').text = earning.concept or ''
            etree.SubElement(item, 'Valor').text = f'{earning.amount:.2f}'
            if earning.quantity:
                etree.SubElement(item, 'Cantidad').text = str(earning.quantity)

        # Deductions
        ded = etree.SubElement(root, 'Deducciones')
        for deduction in self.deduction_ids:
            item = etree.SubElement(ded, 'Concepto')
            etree.SubElement(item, 'Tipo').text = deduction.concept_code or ''
            etree.SubElement(item, 'Descripcion').text = deduction.concept or ''
            etree.SubElement(item, 'Valor').text = f'{deduction.amount:.2f}'
            if deduction.rate:
                etree.SubElement(item, 'Porcentaje').text = f'{deduction.rate:.2f}'

        # Totals
        totals = etree.SubElement(root, 'Totales')
        etree.SubElement(totals, 'DevengadosTotal').text = f'{self.total_earnings:.2f}'
        etree.SubElement(totals, 'DeduccionesTotal').text = f'{self.total_deductions:.2f}'
        etree.SubElement(totals, 'NetoPagar').text = f'{self.net_pay:.2f}'

        return root
