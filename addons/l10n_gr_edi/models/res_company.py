import logging
import requests

from datetime import timedelta
from lxml import etree
from requests import RequestException

from odoo import api, fields, models, Command
from odoo.addons.l10n_gr_edi.models.preferred_classification import INVOICE_TYPES_HAVE_EXPENSE

NS_MYDATA = {"ns": "http://www.aade.gr/myDATA/invoice/v1.0"}

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_gr_edi_aade_id = fields.Char(string='AADE User ID')
    l10n_gr_edi_aade_key = fields.Char(string='AADE Subscription Key')
    l10n_gr_edi_branch_number = fields.Integer(related='partner_id.l10n_gr_edi_branch_number', readonly=False)
    l10n_gr_edi_test_env = fields.Boolean(
        string='Greece Test Environment',
        default=True,
        help="Enable test environments with credentials obtained from https://mydata-dev-register.azurewebsites.net/",
    )

    @api.model
    def _cron_l10n_gr_edi_fetch_invoices(self):
        """ Receive issued MyDATA Invoices and create draft Vendor Bills based on the received XML. """
        gr_companies = self.env['res.company'].search([
            ('l10n_gr_edi_aade_id', '!=', False),
            ('l10n_gr_edi_aade_key', '!=', False),
        ])
        session = requests.Session()
        marks_to_create = []
        bill_create_list_values = []

        for gr_company in gr_companies:
            date_90_days_ago = (fields.Datetime.now() - timedelta(days=90)).strftime("%d/%m/%Y")
            date_today = fields.Datetime.now().strftime("%d/%m/%Y")

            try:
                response = session.get(
                    url="https://mydataapidev.aade.gr/RequestDocs" if gr_company.l10n_gr_edi_test_env else
                        "https://mydatapi.aade.gr/myDATA/RequestDocs",
                    headers={'aade-user-id': gr_company.l10n_gr_edi_aade_id,
                             'ocp-apim-subscription-key': gr_company.l10n_gr_edi_aade_key},
                    params={'mark': 0, 'dateFrom': date_90_days_ago, 'dateTo': date_today},
                    timeout=10,
                )
                response.raise_for_status()
                root = etree.fromstring(response.content)
            except (RequestException, ValueError) as err:
                _logger.error("Something when wrong when fetching MyDATA bill: %s", err)
                continue

            for invoice_element in root.xpath('//*[local-name()="invoice"]'):
                def find_value(element_name):
                    return invoice_element.findtext(f".//ns:{element_name}", namespaces=NS_MYDATA)

                # Make sure not to create duplicate bill in the same company
                if self.env['account.move'].search_count(
                    domain=[
                        ('l10n_gr_edi_mark', '=', find_value('mark')),
                        ('company_id', '=', gr_company.id),
                    ],
                    limit=1,
                ):
                    continue

                # Get invoice lines data
                invoice_line_ids = []
                for detail_element in invoice_element.xpath('.//*[local-name()="invoiceDetails"]'):
                    tax_amount = {'1': 24.0, '2': 13.0, '3': 6.0, '4': 17.0, '5': 9.0, '6': 4.0, '7': 0.0, '8': 0.0}[
                        detail_element.findtext('.//ns:vatCategory', namespaces=NS_MYDATA)]
                    quantity = max(1.0, float(detail_element.findtext('.//ns:quantity', namespaces=NS_MYDATA) or 1))
                    price_unit = float(detail_element.findtext('.//ns:netValue', namespaces=NS_MYDATA)) / quantity
                    invoice_line_ids.append(Command.create({
                        'price_unit': price_unit,
                        'quantity': quantity,
                        'tax_ids': self.env['account.tax'].search(
                            domain=[('amount', '=', tax_amount), ('company_id', '=', gr_company.id)],
                            limit=1,
                        ),
                    }))

                # Collect the bill & document creation data values
                bill_create_list_values.append({
                    'state': 'draft',
                    'move_type': 'in_invoice',
                    'company_id': gr_company.id,
                    'partner_id': self.env['res.partner'].search([('vat', '=', find_value('vatNumber'))], limit=1).id,
                    'date': fields.Date.to_date(find_value('issueDate')),
                    'invoice_date': fields.Date.to_date(find_value('issueDate')),
                    'invoice_line_ids': invoice_line_ids,
                    **({'l10n_gr_edi_inv_type': find_value('invoiceType')} if find_value('invoiceType') in INVOICE_TYPES_HAVE_EXPENSE else {}),
                })
                marks_to_create.append(find_value('mark'))

        if bill_create_list_values and marks_to_create:
            # Create all the fetched bills in batch
            new_bills = self.env['account.move'].sudo().create(bill_create_list_values)

            # Create all the new bills document in batch
            self.env['l10n_gr_edi.document'].create([
                {
                    'state': 'bill_fetched',
                    'move_id': bill.id,
                    'mydata_mark': mark,
                }
                for bill, mark in zip(new_bills, marks_to_create)
            ])
