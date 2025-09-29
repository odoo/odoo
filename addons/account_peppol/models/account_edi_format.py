# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, models, SUPERUSER_ID
from odoo.exceptions import UserError

from odoo.addons.account.models.company import PEPPOL_DEFAULT_COUNTRIES

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _get_proxy_identification(self, company):
        if self.code != 'peppol':
            return super()._get_proxy_identification(company)
        if not company.peppol_eas or not company.peppol_endpoint:
            raise UserError(_("Please fill in the EAS code and the Participant ID code."))
        return f'{company.peppol_eas}:{company.peppol_endpoint}'

    def _get_peppol_builder(self, company):
        if self.code == 'ubl_bis3':
            return self.env['account.edi.xml.ubl_bis3']
        if self.code == 'nlcius_1':
            return self.env['account.edi.xml.ubl_nl']
        if self.code == 'ubl_de':
            return self.env['account.edi.xml.ubl_de']

    def _peppol_post_invoice(self, invoice):
        self.ensure_one()

        edi_format = invoice.commercial_partner_id._get_peppol_edi_format()
        builder = edi_format._get_peppol_builder(invoice.company_id)
        xml_content, errors = builder._export_invoice(invoice)

        attachment_create_vals = {
            'name': builder._export_invoice_filename(invoice),
            'raw': xml_content,
            'mimetype': 'application/xml',
            'res_id': invoice.id,
            'res_model': 'account.move',
        }

        attachment = self.env['ir.attachment'].with_user(SUPERUSER_ID).create(attachment_create_vals)

        res = {invoice: {'attachment': attachment}}
        if errors:
            res[invoice].update({
                'success': False,
                'error': _("Errors occured while creating the Peppol EDI document (format: %s). The receiver "
                           "might refuse it. %s", builder._description, '<p> <li>' + "</li> <li>".join(errors) + '</li> </p>'),
                'blocking_level': 'info',
            })
        else:
            res[invoice]['success'] = True
        return res

    def _get_move_applicability(self, move):
        # EXTENDS account_edi
        if self.code != 'peppol':
            return super()._get_move_applicability(move)

        peppol_edi_format = move.commercial_partner_id._get_peppol_edi_format()
        if peppol_edi_format and move.is_sale_document(include_receipts=False):
            return {'post': self._peppol_post_invoice}

    def _is_compatible_with_journal(self, journal):
        # EXTENDS account_edi
        # the formats appear on the journal only if they are compatible (e.g. NLCIUS only appear for dutch companies)
        self.ensure_one()
        if self.code != 'peppol':
            return super()._is_compatible_with_journal(journal)
        return journal.type == 'sale'

    def _is_enabled_by_default_on_journal(self, journal):
        # EXTENDS account_edi
        self.ensure_one()
        # We want to enable Peppol by default on all journals if the module is installed.
        # (But only for the countries in which Peppol is relevant.)
        # This makes it easier for the user to set up and use Peppol.
        if self.code != 'peppol':
            return super()._is_enabled_by_default_on_journal(journal)
        return self._is_compatible_with_journal(journal) and journal.country_code in PEPPOL_DEFAULT_COUNTRIES
