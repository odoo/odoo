import logging
import requests

from datetime import timedelta
from lxml import etree
from requests import RequestException

from odoo import api, fields, models, Command
from odoo.exceptions import UserError

from odoo.addons.l10n_gr_edi.models.preferred_classification import INVOICE_TYPES_HAVE_EXPENSE, VAT_CATEGORY_TO_RATE

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

    def _l10n_gr_edi_request_documents(self, endpoint):
        self.ensure_one()

        params = {'mark': 0}
        base_url = (
            'https://mydataapidev.aade.gr'
            if self.l10n_gr_edi_test_env
            else 'https://mydatapi.aade.gr/myDATA'
        )

        roots = []
        try:
            with requests.Session() as session:
                while True:
                    response = session.get(
                        url=f'{base_url}/{endpoint}',
                        headers={
                            'aade-user-id': self.l10n_gr_edi_aade_id,
                            'ocp-apim-subscription-key': self.l10n_gr_edi_aade_key,
                        },
                        params=params,
                        timeout=10,
                    )
                    response.raise_for_status()
                    root = etree.fromstring(response.content)
                    if etree.QName(root).localname != 'RequestedDoc':
                        raise UserError(self.env._('Could not retrieve documents from myDATA.'))

                    roots.append(root)
                    next_partition_key = root.xpath(
                        'string(//*[local-name()="continuationToken"]'
                        '/*[local-name()="nextPartitionKey"])'
                    )
                    next_row_key = root.xpath(
                        'string(//*[local-name()="continuationToken"]'
                        '/*[local-name()="nextRowKey"])'
                    )
                    if not next_partition_key or not next_row_key:
                        break
                    params.update({
                        'nextPartitionKey': next_partition_key,
                        'nextRowKey': next_row_key,
                    })
        except (RequestException, etree.XMLSyntaxError) as error:
            raise UserError(self.env._('Could not retrieve documents from myDATA.')) from error

        return roots

    def _l10n_gr_edi_sync_reconciliation(self):
        self.ensure_one()

        transmitted_roots = self._l10n_gr_edi_request_documents('RequestTransmittedDocs')
        counterparty_roots = self._l10n_gr_edi_request_documents('RequestDocs')
        self.env['l10n_gr_edi.reconciliation']._l10n_gr_edi_sync_documents(
            self,
            transmitted_roots,
            counterparty_roots,
            fields.Datetime.now(),
        )

    @api.model
    def _cron_l10n_gr_edi_fetch_invoices(self):
        """ Receive issued myDATA Invoices and create draft Vendor Bills based on the received XML. """
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
                _logger.error("Something when wrong when fetching myDATA bill: %s", err)
                continue

            chart_template = self.env['account.chart.template'].with_company(gr_company)
            article_31_purchase_taxes = {
                9: chart_template.ref('l10n_gr_tax_p3_S_art31'),
                10: chart_template.ref('l10n_gr_tax_p4_S_art31'),
            }
            article_31_purchase_tax_ids = [tax.id for tax in article_31_purchase_taxes.values()]

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
                    vat_category = int(detail_element.findtext('.//ns:vatCategory', namespaces=NS_MYDATA))
                    tax = article_31_purchase_taxes.get(vat_category)
                    if not tax:
                        tax = self.env['account.tax'].search(
                            domain=[
                                ('amount', '=', VAT_CATEGORY_TO_RATE[vat_category]),
                                ('company_id', '=', gr_company.id),
                                ('type_tax_use', '=', 'purchase'),
                                ('id', 'not in', article_31_purchase_tax_ids),
                            ],
                            limit=1,
                        )
                    quantity = max(1.0, float(detail_element.findtext('.//ns:quantity', namespaces=NS_MYDATA) or 1))
                    price_unit = float(detail_element.findtext('.//ns:netValue', namespaces=NS_MYDATA)) / quantity
                    invoice_line_ids.append(Command.create({
                        'price_unit': price_unit,
                        'quantity': quantity,
                        'tax_ids': tax,
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
