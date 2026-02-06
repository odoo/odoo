# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


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
    # DIAN Post / Cancel — Stubs for Phase 2-3 implementation
    # =====================================================================

    def _l10n_co_edi_post_invoice(self, invoices):
        """Generate UBL XML, sign it, compute CUFE/CUDE, and send to DIAN.

        This is the main entry point called by the EDI framework when an
        invoice is posted. Full implementation in Phase 2 (XML generation)
        and Phase 3 (DIAN web service).

        :param invoices: account.move recordset
        :return: dict mapping move to result dict
        """
        result = {}
        for invoice in invoices:
            # Phase 1: Compute CUFE/CUDE and set EDI datetime
            invoice.l10n_co_edi_datetime = invoice.l10n_co_edi_datetime or invoice.create_date
            invoice.l10n_co_edi_compute_cufe_cude()
            invoice.l10n_co_edi_state = 'pending'

            # TODO Phase 2: Generate UBL 2.1 XML
            # TODO Phase 2: Sign XML with digital certificate
            # TODO Phase 3: Submit to DIAN web service
            # TODO Phase 3: Process DIAN response

            # For now, mark as pending (will be processed by cron in Phase 3)
            result[invoice] = {
                'success': True,
                'blocking_level': 'info',
            }
        return result

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

        Stub — full implementation in Phase 2.

        :param invoice: account.move record
        :return: bytes (XML content)
        """
        # TODO Phase 2: Full UBL 2.1 XML generation
        return b'<?xml version="1.0" encoding="UTF-8"?><!-- Placeholder: Phase 2 -->'
