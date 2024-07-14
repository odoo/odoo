# -*- coding: utf-8 -*-

import base64
import tempfile
import re
import zipfile

from collections import Counter

from lxml import etree

from odoo import _, fields, models, api, Command
from odoo.exceptions import UserError
from .ONSS_country_mapping import ONSS_COUNTRY_CODE_MAPPING


def format_if_float(amount):
    return f"{amount * 100:.0f}" if isinstance(amount, float) else amount  # amounts in € requires to be formatted for xml

def format_325_form_values(values):
    tmp_dict = {}
    for key, value in values.items():
        if isinstance(value, list):
            tmp_dict[key] = [format_325_form_values(v) for v in value]
        else:
            tmp_dict[key] = format_if_float(value)
    return tmp_dict

class Form325(models.Model):
    _name = "l10n_be.form.325"
    _description = "Represents a 325 form"
    _inherit = ['mail.thread']

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('generated', 'Generated'),
        ],
        default='draft',
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        string='Debtor company',
        help='Debtor for which the form is created',
        readonly=True,
    )

    user_id = fields.Many2one('res.users')

    sender_id = fields.Many2one(
        'res.partner',
        string='Sender',
        required=True,
        ondelete='restrict',
    )
    sender_name = fields.Char(
        string='Sender Name',
        compute='_compute_sender_name', store=True,
    )
    sender_address = fields.Char(
        string='Sender Address',
        compute='_compute_sender_address', store=True,
    )
    sender_zip = fields.Char(
        string='Sender ZIP',
        compute='_compute_sender_zip', store=True,
    )
    sender_city = fields.Char(
        string='Sender City',
        compute='_compute_sender_city', store=True,
    )
    sender_phone_number = fields.Char(
        string='Sender Phone Number',
        compute='_compute_sender_phone_number', store=True,
    )
    sender_lang_code = fields.Selection(
        [
            ('1', 'Dutch'),
            ('2', 'French'),
            ('3', 'German'),
        ],
        compute='_compute_sender_lang_code', store=True,
        string='Sender Language Code',
    )
    sender_bce_number = fields.Char(
        string='Sender BCE Number',
        compute='_compute_sender_bce_number', store=True,
    )

    debtor_id = fields.Many2one(
        'res.partner',
        string='Debtor',
        related='company_id.partner_id', store=True,
        ondelete='restrict',
    )
    debtor_name = fields.Char(
        string='Debtor Name',
        compute='_compute_debtor_name', store=True,
    )
    debtor_address = fields.Char(
        string='Debtor Address',
        compute='_compute_debtor_address', store=True,
    )
    debtor_zip = fields.Char(
        string='Debtor ZIP',
        compute='_compute_debtor_zip', store=True,
    )
    debtor_city = fields.Char(
        string='Debtor City',
        compute='_compute_debtor_city', store=True,
    )
    debtor_phone_number = fields.Char(
        string='Debtor Phone Number',
        compute='_compute_debtor_phone_number', store=True,
    )
    debtor_country_id = fields.Many2one(
        'res.country',
        string='Debtor Country',
        ondelete='restrict',
        compute='_compute_debtor_country_id', store=True,
    )
    debtor_bce_number = fields.Char(
        string='Debtor BCE Number',
        compute='_compute_debtor_bce_number', store=True,
    )
    debtor_is_natural_person = fields.Char(
        string='Debtor is Natural Person',
        compute='_compute_debtor_is_natural_person', store=True,
    )
    debtor_citizen_identification = fields.Char(
        string='Debtor Citizen Identification',
        compute='_compute_debtor_citizen_identification', store=True,
    )

    reference_year = fields.Char(
        string='Reference Year',
        required=True,
        default=lambda x: str(fields.Date.context_today(x).year - 1),
        readonly=True,
    )
    is_test = fields.Boolean(
        string="Test Form",
        help="Indicates if the 325 is a test",
        required=True,
        default=False,
        tracking=True,
    )
    sending_type = fields.Selection(
        [
            ('0', 'Original send'),
            ('1', 'Send grouped corrections'),
        ],
        string='Sending type',
        default='0',
        required=True,
        help="This field allows to make an original sending(correspond to first send) "
             "or a grouped corrections(if you have made some mistakes before).",
        tracking=True,
    )
    treatment_type = fields.Selection([
            ('0', 'Original'),
            ('1', 'Modification'),
            ('2', 'Add'),
            ('3', 'Cancel'),
        ],
        string="Treatment Type",
        default='0',
        required=True,
        help="This field represents the nature of the form.",
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
    )
    form_281_50_ids = fields.One2many('l10n_be.form.281.50', 'form_325_id', string='Forms 281.50')
    form_281_50_count = fields.Integer(string='Forms 281.50 count', compute='_compute_form_281_50_count')
    form_281_50_total_amount = fields.Monetary(
        string='Forms 281.50 total',
        compute='_compute_form_281_50_total_amount',
    )

    @api.depends('reference_year', 'is_test')
    def _compute_display_name(self):
        for f_325 in self:
            f_325.display_name = f"325 - {f_325.reference_year}{' - TEST' if f_325.is_test else ''}"

    @api.depends('form_281_50_ids')
    def _compute_form_281_50_count(self):
        for record in self:
            record.form_281_50_count = len(record.form_281_50_ids)

    @api.depends('form_281_50_ids')
    def _compute_form_281_50_total_amount(self):
        for record in self:
            record.form_281_50_total_amount = sum(record.form_281_50_ids.mapped('total_remuneration'))

    @api.depends('state', 'sender_id', 'sender_id.name')
    def _compute_sender_name(self):
        for form in self:
            if form.state == 'draft':
                form.sender_name = form.sender_id.name

    @api.depends('state', 'sender_id', 'sender_id.street', 'sender_id.street2')
    def _compute_sender_address(self):
        for form in self:
            if form.state == 'draft':
                form.sender_address = form.sender_id._formated_address()

    @api.depends('state', 'sender_id', 'sender_id.zip')
    def _compute_sender_zip(self):
        for form in self:
            if form.state == 'draft':
                form.sender_zip = form.sender_id.zip

    @api.depends('state', 'sender_id', 'sender_id.city')
    def _compute_sender_city(self):
        for form in self:
            if form.state == 'draft':
                form.sender_city = form.sender_id.city

    @api.depends('state', 'sender_id', 'sender_id.phone')
    def _compute_sender_phone_number(self):
        for form in self:
            if form.state == 'draft':
                form.sender_phone_number = re.sub(r"\D", '', form.sender_id.phone)

    @api.depends('state', 'sender_id', 'sender_id.lang')
    def _compute_sender_lang_code(self):
        for form in self:
            if form.state == 'draft':
                form.sender_lang_code = form.sender_id._get_lang_code()

    @api.depends('state', 'sender_id', 'sender_id.vat')
    def _compute_sender_bce_number(self):
        for form in self:
            if form.state == 'draft':
                form.sender_bce_number = form.sender_id._get_bce_number()

    @api.depends('state', 'debtor_id', 'debtor_id.name')
    def _compute_debtor_name(self):
        for form in self:
            if form.state == 'draft':
                form.debtor_name = form.debtor_id.name

    @api.depends('state', 'debtor_id', 'debtor_id.street', 'debtor_id.street2')
    def _compute_debtor_address(self):
        for form in self:
            if form.state == 'draft':
                form.debtor_address = form.debtor_id._formated_address()

    @api.depends('state', 'debtor_id', 'debtor_id.zip')
    def _compute_debtor_zip(self):
        for form in self:
            if form.state == 'draft':
                form.debtor_zip = form.debtor_id.zip

    @api.depends('state', 'debtor_id', 'debtor_id.city')
    def _compute_debtor_city(self):
        for form in self:
            if form.state == 'draft':
                form.debtor_city = form.debtor_id.city

    @api.depends('state', 'debtor_id', 'debtor_id.phone')
    def _compute_debtor_phone_number(self):
        for form in self:
            if form.state == 'draft':
                form.debtor_phone_number = form.debtor_id.phone

    @api.depends('state', 'debtor_id', 'debtor_id.country_id')
    def _compute_debtor_country_id(self):
        for form in self:
            if form.state == 'draft':
                form.debtor_country_id = form.debtor_id.country_id.id

    @api.depends('state', 'debtor_id', 'debtor_id.is_company', 'debtor_id.vat')
    def _compute_debtor_bce_number(self):
        for form in self:
            if form.state == 'draft':
                if form.debtor_id.is_company:
                    form.debtor_bce_number = form.debtor_id._get_bce_number()

    @api.depends('state', 'debtor_id', 'debtor_id.is_company')
    def _compute_debtor_is_natural_person(self):
        for form in self:
            if form.state == 'draft':
                form.debtor_is_natural_person = not bool(form.debtor_id.is_company)

    @api.depends('state', 'debtor_id', 'debtor_id.is_company', 'debtor_id.citizen_identification')
    def _compute_debtor_citizen_identification(self):
        for form in self:
            if form.state == 'draft':
                if not form.debtor_id.is_company:
                    form.debtor_citizen_identification = form.debtor_id.citizen_identification

    def write(self, vals):
        for form_325 in self:
            if 'state' in vals and form_325.state == 'generated':
                vals.pop('state')

        return super().write(vals)

    def _generate_form_281_50(self):
        """Compute, create and link the 281.50 records"""
        self.ensure_one()
        if self.form_281_50_count > 0:
            raise UserError(_("You already generated 281.50 forms for this 325 form."))
        partner_tag_id = self.env.ref('l10n_be_reports.res_partner_tag_281_50').id
        partner_ids = self.env['res.partner'].search([
            ('category_id', '=', partner_tag_id),
        ])
        partner_281_50_form_values = self._get_remuneration_281_50_per_partner(partner_ids)
        self.write({'form_281_50_ids': [Command.create(vals) for vals in partner_281_50_form_values]})

    @api.model
    def _get_remuneration_281_50_per_partner(self, partner_ids):
        tag_281_50_atn, tag_281_50_commissions, tag_281_50_exposed_expenses, tag_281_50_fees = self._get_281_50_tags()
        account_281_50_tags = tag_281_50_commissions + tag_281_50_fees + tag_281_50_atn + tag_281_50_exposed_expenses

        self.env.flush_all()
        commissions_per_partner = self._get_balance_per_partner(partner_ids, tag_281_50_commissions)
        fees_per_partner = self._get_balance_per_partner(partner_ids, tag_281_50_fees)
        atn_per_partner = self._get_balance_per_partner(partner_ids, tag_281_50_atn)
        exposed_expenses_per_partner = self._get_balance_per_partner(partner_ids, tag_281_50_exposed_expenses)
        paid_amount_per_partner = self._get_paid_amount_per_partner(partner_ids, account_281_50_tags)

        partner_ids = self.env['res.partner'].browse(
            set().union(
                commissions_per_partner,
                fees_per_partner,
                atn_per_partner,
                exposed_expenses_per_partner,
                paid_amount_per_partner
            )
        )

        if not partner_ids:
            raise UserError(_(
                "Either there isn't any account nor partner with a 281.50 tag "
                "or there isn't any amount to report for this period."
            ))

        partner_ids._check_partner_281_50_required_values()

        amount_per_partner = [
            {
                'partner_id': partner_id.id,
                'commissions': commissions_per_partner.get(partner_id.id, 0.0),
                'fees': fees_per_partner.get(partner_id.id, 0.0),
                'atn': atn_per_partner.get(partner_id.id, 0.0),
                'exposed_expenses': exposed_expenses_per_partner.get(partner_id.id, 0.0),
                'paid_amount': paid_amount_per_partner.get(partner_id.id, 0.0),
            }
            for partner_id in partner_ids.sorted(lambda p: (p.zip, p.name))
        ]

        return amount_per_partner

    def _get_balance_per_partner(self, partners, tag_ids):
        """Returns a dict such as {partner_id: expense_related_to_tag_ids}

            for each partner following some rules:
                - All account.move.line have an account with the "281.50 - XXXXX" tag.
                - All account.move.line must be between the first day and the last day
                of the reference year.
                - All account.move.line must be in a posted account.move.
            These information are group by partner!
            :param tag_ids: used to compute the balance (normally account with 281.50 - XXXXX tag).
            :return: {partner_id: float}
        """
        accounts = self.env['account.account'].search([('tag_ids', 'in', tag_ids.ids)])
        if not accounts:
            return {}

        self.env.cr.execute("""
            SELECT COALESCE(move.commercial_partner_id, line.partner_id),
                   ROUND(SUM(line.balance), %(decimal_places)s) AS balance
              FROM account_move_line line
              JOIN account_move move on line.move_id = move.id
             WHERE COALESCE(move.commercial_partner_id, line.partner_id) = ANY(%(partners)s)
               AND line.account_id = ANY(%(accounts)s)
               AND line.date BETWEEN %(move_date_from)s AND %(move_date_to)s
               AND line.parent_state = 'posted'
               AND line.company_id = %(company)s
          GROUP BY COALESCE(move.commercial_partner_id, line.partner_id)
        """, {
            'partners': partners.ids,
            'accounts': accounts.ids,
            'move_date_from': f'{self.reference_year}-01-01',
            'move_date_to': f'{self.reference_year}-12-31',
            'company': self.env.company.id,
            'decimal_places': self.env.company.currency_id.decimal_places,
        })
        return dict(self.env.cr.fetchall())
    @api.model
    def _get_281_50_tags(self):
        missing_tag = []

        def try_to_load_tags(xml_id):
            tag = self.env.ref(xml_id, raise_if_not_found=False)
            if not tag:
                missing_tag.append(xml_id)
            return tag

        tag_281_50_commissions = try_to_load_tags('l10n_be_reports.account_tag_281_50_commissions')
        tag_281_50_fees = try_to_load_tags('l10n_be_reports.account_tag_281_50_fees')
        tag_281_50_atn = try_to_load_tags('l10n_be_reports.account_tag_281_50_atn')
        tag_281_50_exposed_expenses = try_to_load_tags('l10n_be_reports.account_tag_281_50_exposed_expenses')
        if missing_tag:
            raise UserError(_("Internal reference to the following 281.50 tags are missing:\n") + missing_tag)
        return tag_281_50_atn, tag_281_50_commissions, tag_281_50_exposed_expenses, tag_281_50_fees

    def _get_paid_amount_per_partner(self, partner_ids, tags):
        """Get all paid amount per partner for a specific year and the previous year.

            :param partner_ids: Partner to compute paid amount.
            :param tags: Which tags to get paid amount for
            :return: A dict of paid amount (for the specific year and the previous year) per partner.
        """
        self.env.cr.execute("""
        WITH paid_expense_line AS (
            SELECT aml_payable.id AS payable_id,
                   COALESCE(move_payable.commercial_partner_id, aml_payable.partner_id) as partner_id,
                   aml_expense.move_id,
                   aml_expense.balance
              FROM account_move_line aml_payable
              JOIN account_move move_payable ON aml_payable.move_id = move_payable.id
              JOIN account_account account ON aml_payable.account_id = account.id
              JOIN account_move_line aml_expense ON aml_payable.move_id = aml_expense.move_id
              JOIN account_account_account_tag account_tag_rel ON aml_expense.account_id = account_tag_rel.account_account_id
             WHERE account_tag_rel.account_account_tag_id = ANY(%(tag_ids)s)
               AND account.account_type IN ('liability_payable', 'asset_receivable')
               AND aml_payable.parent_state = 'posted'
               AND aml_payable.company_id = %(company_id)s
               AND aml_payable.date BETWEEN %(invoice_date_from)s AND %(invoice_date_to)s
               AND aml_expense.date BETWEEN %(invoice_date_from)s AND %(invoice_date_to)s
               AND COALESCE(move_payable.commercial_partner_id, aml_payable.partner_id) = ANY(%(partner_ids)s)
        ),
        amount_paid_per_partner_based_on_bill_reconciled AS (
            SELECT paid_expense_line.partner_id AS partner_id,
                    -- amount_total_signed is negative for in_invoice
                   SUM((apr.amount / ABS(move.amount_total_signed)) * (paid_expense_line.balance)) AS paid_amount
              FROM paid_expense_line
              JOIN account_move move ON paid_expense_line.move_id = move.id
              JOIN account_partial_reconcile apr ON paid_expense_line.payable_id = apr.credit_move_id OR paid_expense_line.payable_id = apr.debit_move_id
              JOIN account_move_line aml_payment ON aml_payment.id = apr.debit_move_id
             WHERE aml_payment.parent_state = 'posted'
               AND apr.max_date BETWEEN %(payment_date_from)s AND %(payment_date_to)s
          GROUP BY paid_expense_line.partner_id
        ),
        amount_send_to_expense_without_bill AS (
            SELECT line.partner_id,
                   line.balance AS paid_amount
              FROM account_move_line AS line
              JOIN account_journal journal ON journal.id = line.journal_id
              JOIN account_account_account_tag account_tag_rel ON line.account_id = account_tag_rel.account_account_id
             WHERE line.company_id = %(company_id)s
               AND journal.type IN ('bank', 'cash')
               AND line.parent_state = 'posted'
               AND account_tag_rel.account_account_tag_id = ANY(%(tag_ids)s)
               AND line.date BETWEEN %(payment_date_from)s AND %(payment_date_to)s
               AND line.partner_id = ANY(%(partner_ids)s)
        ),
        amount_paid AS (
            SELECT * FROM amount_paid_per_partner_based_on_bill_reconciled
         UNION ALL
            SELECT * FROM amount_send_to_expense_without_bill
        )
        SELECT sub.partner_id, ROUND(SUM(sub.paid_amount), %(decimal_places)s) AS paid_amount
          FROM amount_paid AS sub
      GROUP BY sub.partner_id
        """, {
            'company_id': self.company_id.id,
            'payment_date_from': f'{self.reference_year}-01-01',
            'payment_date_to': f'{self.reference_year}-12-31',
            'invoice_date_from': f'{int(self.reference_year) - 1}-01-01',
            'invoice_date_to': f'{self.reference_year}-12-31',
            'tag_ids': tags.ids,
            'partner_ids': partner_ids.ids,
            'decimal_places': self.currency_id.decimal_places,
        })
        return dict(self.env.cr.fetchall())

    def action_generate_281_50_form_file(self, file_types=('xml', 'pdf')):
        self.ensure_one()
        attachments = []
        if 'xml' in file_types:
            file_name = f"{self.reference_year}-325.50{'-test' if self.is_test else ''}.xml"
            attachments.append((file_name, self._generate_325_form_xml()))
        if 'pdf' in file_types:
            for form_281_50 in self.form_281_50_ids:
                attachments.append((form_281_50._get_pdf_file_name(), form_281_50._generate_281_50_form_pdf()))

        if len(attachments) > 1:  # If there are more than one file, we zip all these files.
            downloaded_filename = f"281_50_forms_{self.reference_year}.zip"
            with tempfile.SpooledTemporaryFile() as tmp_file:  # We store the zip into a temporary file.
                with zipfile.ZipFile(tmp_file, 'w', zipfile.ZIP_DEFLATED) as archive:  # We create the zip archive.
                    for attach in attachments:  # And we store each file in the archive.
                        archive.writestr(attach[0], attach[1])
                tmp_file.seek(0)

                self.env['ir.attachment'].create({
                    'name': downloaded_filename,
                    'raw': tmp_file.read(),
                    'res_model': 'l10n_be.form.325',
                    'res_id': self.id,
                })
        else:  # If there is only one file, we download the file directly.
            downloaded_filename, contents = attachments[0]
            self.env['ir.attachment'].create({
                'name': downloaded_filename,
                'raw': contents,
                'res_model': 'l10n_be.form.325',
                'res_id': self.id,
            })

        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_generate_281_50_form_xml(self):
        return self.action_generate_281_50_form_file(file_types=('xml',))

    def action_generate_281_50_form_pdf(self):
        return self.action_generate_281_50_form_file(file_types=('pdf',))

    def action_generate_325_form_pdf(self):
        self.ensure_one()
        pdf_file, dummy = self.env['ir.actions.report']._render_qweb_pdf("l10n_be_reports.action_report_325_form_pdf", self, data=self._get_325_form_values())
        self.env['ir.attachment'].create({
            'name': f"{self.reference_year}_325_form.pdf",
            'datas': base64.b64encode(pdf_file),
            'res_model': 'l10n_be.form.325',
            'res_id': self.id,
        })
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _generate_325_form_xml(self):
        """Create the 325 xml file and return a stringified version."""
        self.ensure_one()
        self._validate_form()
        form_values = self.get_dict_values()
        formated_form_values = format_325_form_values(form_values)
        xml, dummy = self.env["ir.actions.report"]._render_qweb_text('l10n_be_reports.action_report_partner_281_50_xml', self, formated_form_values)
        xml_element = etree.fromstring(xml)
        return etree.tostring(xml_element, xml_declaration=True, encoding='utf-8')  # Well format the xml and add the xml_declaration

    def _validate_form(self):
        # Once the xml is generated, the 325 and 281.50 forms are in the generated state and can't be edited
        # We save all information from sender and debtor in the form.
        self.ensure_one()
        if self.state != 'generated':
            self.form_281_50_ids.assign_official_id()
            self.write({
                'state': 'generated',
                'user_id': self.env.user,
            })

    def get_dict_values(self):
        self.ensure_one()
        return self._get_sender_dict_values()

    def _get_sender_dict_values(self):
        self.ensure_one()
        debtor_form = self._get_debtor_dict_values()
        return {
            'V0002': self.reference_year,
            'V0010': "BELCOTST" if self.is_test else "BELCOTAX",
            'V0011': fields.Date.today().strftime('%d-%m-%Y'),
            'V0014': self.sender_name,
            'V0015': self.sender_address,
            'V0016': self.sender_zip,
            'V0017': self.sender_city,
            'V0018': self.sender_phone_number,
            'V0021': self.user_id.name,
            'V0022': self.sender_lang_code,
            'V0023': self.user_id.email,
            'V0024': self.sender_bce_number,
            'V0025': self.sending_type,
            **debtor_form,
            'R9002': self.reference_year,
            'R9010': 3,  # from the xml validation: number of report (aangifte) + 2
            'R9011': 2 + debtor_form.get('R8010'),  # sum of all R8010 + 2 (1 for the V fields and 1 for R fields)
            'R9012': debtor_form.get('R8011'),  # sum all sequences
            'R9013': debtor_form.get('R8012'),  # sum of all 8012
        }

    def _get_debtor_dict_values(self):
        self.ensure_one()
        partner_281_50_forms = [form.get_dict_values() for form in self.form_281_50_ids]
        return {
            'A1002': self.reference_year,
            'A1005': self.debtor_bce_number,
            'A1011': self.debtor_name,
            'A1013': self.debtor_address,
            'A1014': self.debtor_zip,
            'A1015': self.debtor_city,
            'A1016': ONSS_COUNTRY_CODE_MAPPING.get(self.debtor_country_id.code),
            'A1020': 1,
            'Fiches28150': partner_281_50_forms,  # Official name from the XML
            'R8002': self.reference_year,
            'R8005': self.debtor_bce_number,
            'R8010': 2 + len(partner_281_50_forms),
            # number of record for this declaration: A1XXX + R8XXX + Fiches28150
            'R8011': sum((form.get('F2009') for form in partner_281_50_forms)),  # Sum sequence
            'R8012': sum((p.get('F50_2059') for p in partner_281_50_forms)),  # Total control
        }

    def _get_325_form_values(self):
        self.ensure_one()
        form_325_values = []
        forms_325_50_values = []
        form_325_50_old_sum = 0
        for index, form_281_50 in enumerate(self.form_281_50_ids):
            forms_325_50_values.append(form_281_50)
            if len(self.form_281_50_ids) - 1 == index or index != 0 and index % 5 == 0:
                form_325_50_sum = sum([form.total_remuneration for form in forms_325_50_values]) + form_325_50_old_sum
                form_325_values.append({
                    'form_325_50_old_sum': form_325_50_old_sum,
                    'forms_325_50_values': forms_325_50_values,
                    'form_325_50_sum': form_325_50_sum,
                })
                form_325_50_old_sum = form_325_50_sum
                forms_325_50_values = []
        return {'forms_325_50': form_325_values}

    def unlink(self):
        self.form_281_50_ids.unlink()
        return super().unlink()

    @api.ondelete(at_uninstall=False)
    def _unlink_only_if_state_not_generated_and_not_test(self):
        if self.filtered(lambda f_325: f_325.state == 'generated' and not f_325.is_test):
            raise UserError(_("You can't delete a 281.50 for which its form 325 xml has been generated"))
