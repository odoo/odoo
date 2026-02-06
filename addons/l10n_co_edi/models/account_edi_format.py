# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging

from odoo import api, models, _

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _get_move_applicability(self, move):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'co_dian':
            return super()._get_move_applicability(move)

        if move.company_id.account_fiscal_country_id.code != 'CO':
            return None

        if move.move_type in ('out_invoice', 'out_refund'):
            return {
                'post': self._l10n_co_edi_post_invoice,
                'cancel': self._l10n_co_edi_cancel_invoice,
                'edi_content': self._l10n_co_edi_get_xml_content,
            }
        return None

    def _needs_web_services(self):
        # OVERRIDE
        self.ensure_one()
        return self.code == 'co_dian' or super()._needs_web_services()

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        self.ensure_one()
        if self.code == 'co_dian':
            return (
                journal.type in ('sale', 'purchase')
                and journal.company_id.account_fiscal_country_id.code == 'CO'
            )
        return super()._is_compatible_with_journal(journal)

    def _is_enabled_by_default_on_journal(self, journal):
        # OVERRIDE
        self.ensure_one()
        if self.code == 'co_dian':
            return journal.company_id.account_fiscal_country_id.code == 'CO'
        return super()._is_enabled_by_default_on_journal(journal)

    def _check_move_configuration(self, move):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'co_dian':
            return super()._check_move_configuration(move)

        errors = []
        company = move.company_id
        journal = move.journal_id

        if not company.vat:
            errors.append(_('The company %s must have a NIT configured.', company.name))

        if not company.l10n_co_edi_software_id:
            errors.append(_('DIAN Software ID is not configured. Go to Settings > Accounting > Colombian Electronic Invoicing.'))

        if not company.l10n_co_edi_software_pin:
            errors.append(_('DIAN Software PIN is not configured.'))

        if not company.l10n_co_edi_certificate:
            errors.append(_('No digital certificate uploaded. A valid .p12 certificate is required.'))

        if move.move_type == 'out_invoice' and not journal.l10n_co_edi_dian_technical_key:
            errors.append(_('DIAN Technical Key (Clave Tecnica) is not configured on journal %s.', journal.name))

        if not journal.l10n_co_edi_dian_authorization:
            errors.append(_('DIAN Authorization Number is not configured on journal %s.', journal.name))

        partner = move.commercial_partner_id
        if not partner.vat and not partner.l10n_latam_identification_type_id:
            errors.append(_('Customer %s must have an identification number (NIT/CC/CE).', partner.name))

        # Check numbering range
        if journal.l10n_co_edi_dian_range_to and journal.l10n_co_edi_range_remaining <= 0:
            errors.append(_('DIAN numbering range exhausted on journal %s. Request a new range from DIAN.', journal.name))

        if journal.l10n_co_edi_dian_range_valid_to and journal.l10n_co_edi_dian_range_valid_to < move.invoice_date:
            errors.append(_('DIAN numbering range on journal %s has expired (valid until %s).',
                          journal.name, journal.l10n_co_edi_dian_range_valid_to))

        return errors

    # =====================================================================
    # Colombian UBL Builder Access
    # =====================================================================

    def _l10n_co_edi_get_ubl_builder(self):
        """Return the Colombian UBL 2.1 XML builder instance."""
        return self.env['account.edi.xml.ubl_co']

    # =====================================================================
    # DIAN Post / Cancel / Content
    # =====================================================================

    def _l10n_co_edi_post_invoice(self, invoices):
        """Generate UBL XML, sign it, compute CUFE/CUDE, and send to DIAN.

        Flow:
        1. Set EDI datetime and compute CUFE/CUDE
        2. Generate DIAN-compliant UBL 2.1 XML
        3. Sign with digital certificate (XMLDSig/XAdES-BES)
        4. Store the signed XML on the invoice
        5. (Phase 3) Submit to DIAN web service

        :param invoices: account.move recordset
        :return: dict mapping move to result dict
        """
        builder = self._l10n_co_edi_get_ubl_builder()
        result = {}

        for invoice in invoices:
            try:
                # 1. Compute CUFE/CUDE and set EDI datetime
                invoice.l10n_co_edi_datetime = invoice.l10n_co_edi_datetime or invoice.create_date
                invoice.l10n_co_edi_compute_cufe_cude()

                # 2. Generate UBL 2.1 XML
                xml_content, errors = builder._export_invoice(invoice)

                if errors:
                    _logger.warning(
                        'Invoice %s: XML generation warnings: %s',
                        invoice.name, ', '.join(errors),
                    )

                # 3. Sign with digital certificate
                xml_content = self._l10n_co_edi_sign_xml(invoice, xml_content)

                # 4. Store signed XML
                filename = builder._export_invoice_filename(invoice)
                invoice.l10n_co_edi_xml_file = base64.b64encode(xml_content)
                invoice.l10n_co_edi_xml_filename = filename
                invoice.l10n_co_edi_state = 'pending'

                # TODO Phase 3: Submit to DIAN web service
                # TODO Phase 3: Process DIAN response (validate/reject)

                result[invoice] = {
                    'success': True,
                    'blocking_level': 'info',
                    'attachment': self.env['ir.attachment'].create({
                        'name': filename,
                        'raw': xml_content,
                        'mimetype': 'application/xml',
                        'res_model': invoice._name,
                        'res_id': invoice.id,
                    }),
                }

            except Exception as e:
                _logger.exception('Error generating DIAN XML for invoice %s', invoice.name)
                result[invoice] = {
                    'success': False,
                    'error': _('Error generating electronic invoice: %s', str(e)),
                    'blocking_level': 'error',
                }

        return result

    def _l10n_co_edi_sign_xml(self, invoice, xml_content):
        """Sign XML with the company's digital certificate.

        If no certificate is configured (e.g., in test mode), returns
        the unsigned XML with a warning.

        :param invoice: account.move record
        :param xml_content: bytes — unsigned UBL XML
        :return: bytes — signed UBL XML (or unsigned if no cert)
        """
        company = invoice.company_id
        if not company.l10n_co_edi_certificate:
            _logger.info(
                'Invoice %s: No digital certificate configured, returning unsigned XML.',
                invoice.name,
            )
            return xml_content

        try:
            from odoo.addons.l10n_co_edi.tools.xml_signer import DianXmlSigner

            cert_data = base64.b64decode(company.l10n_co_edi_certificate)
            password = company.l10n_co_edi_certificate_password or ''
            signer = DianXmlSigner(cert_data, password)
            return signer.sign(xml_content)
        except ImportError:
            _logger.warning(
                'Invoice %s: cryptography library not available, returning unsigned XML.',
                invoice.name,
            )
            return xml_content
        except Exception as e:
            _logger.error(
                'Invoice %s: Error signing XML: %s. Returning unsigned.',
                invoice.name, str(e),
            )
            return xml_content

    def _l10n_co_edi_cancel_invoice(self, invoices):
        """Request cancellation of a validated electronic invoice with DIAN.

        In Colombia, invoices cannot be directly cancelled — a credit note
        must be issued instead. This method handles the EDI cancellation flow.

        :param invoices: account.move recordset
        :return: dict mapping move to result dict
        """
        result = {}
        for invoice in invoices:
            # TODO Phase 3: Submit cancellation to DIAN
            invoice.l10n_co_edi_state = 'cancelled'
            result[invoice] = {'success': True}
        return result

    def _l10n_co_edi_get_xml_content(self, invoice):
        """Return the UBL 2.1 XML content for the invoice.

        If the XML has already been generated and stored, return it.
        Otherwise, generate it fresh.

        :param invoice: account.move record
        :return: bytes (XML content)
        """
        if invoice.l10n_co_edi_xml_file:
            return base64.b64decode(invoice.l10n_co_edi_xml_file)

        builder = self._l10n_co_edi_get_ubl_builder()
        xml_content, _errors = builder._export_invoice(invoice)
        return xml_content
