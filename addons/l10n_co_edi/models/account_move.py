# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from .l10n_co_edi_cufe import compute_cufe, compute_cude


class AccountMove(models.Model):
    _inherit = 'account.move'

    # -- DIAN Electronic Invoicing Fields --
    l10n_co_edi_cufe_cude = fields.Char(
        string='CUFE/CUDE',
        copy=False,
        readonly=True,
        help='Unique electronic invoice code (CUFE for invoices, CUDE for credit/debit notes).',
    )
    l10n_co_edi_state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('sent', 'Sent to DIAN'),
            ('validated', 'Validated by DIAN'),
            ('rejected', 'Rejected by DIAN'),
            ('cancelled', 'Cancelled'),
        ],
        string='DIAN Status',
        copy=False,
        readonly=True,
        tracking=True,
        help='Status of this document with DIAN electronic invoicing system.',
    )
    l10n_co_edi_xml_file = fields.Binary(
        string='UBL XML File',
        copy=False,
        readonly=True,
        attachment=True,
        help='Generated UBL 2.1 XML document.',
    )
    l10n_co_edi_xml_filename = fields.Char(
        string='XML Filename',
        copy=False,
    )
    l10n_co_edi_qr_data = fields.Char(
        string='QR Code Data',
        copy=False,
        readonly=True,
        help='Data encoded in the QR code on the graphic representation.',
    )
    l10n_co_edi_dian_response = fields.Text(
        string='DIAN Response',
        copy=False,
        readonly=True,
        help='Raw response from DIAN validation service.',
    )
    l10n_co_edi_dian_response_status = fields.Char(
        string='DIAN Response Code',
        copy=False,
        readonly=True,
    )
    l10n_co_edi_datetime = fields.Datetime(
        string='EDI Date/Time',
        copy=False,
        readonly=True,
        help='Timestamp used for CUFE/CUDE computation (set at posting time).',
    )

    # -- Computed --
    l10n_co_edi_is_colombian = fields.Boolean(
        compute='_compute_l10n_co_edi_is_colombian',
    )

    @api.depends('company_id.account_fiscal_country_id')
    def _compute_l10n_co_edi_is_colombian(self):
        for move in self:
            move.l10n_co_edi_is_colombian = (
                move.company_id.account_fiscal_country_id.code == 'CO'
            )

    def l10n_co_edi_compute_cufe_cude(self):
        """Compute the CUFE or CUDE for this move.

        CUFE is used for sales invoices.
        CUDE is used for credit notes, debit notes, and equivalent documents.
        """
        for move in self:
            if not move.l10n_co_edi_is_colombian:
                continue

            # Collect tax amounts by DIAN type code
            tax_totals = move._l10n_co_edi_get_tax_totals_by_type()
            iva_amount = tax_totals.get('01', 0.0)   # IVA
            inc_amount = tax_totals.get('04', 0.0)   # INC
            ica_amount = tax_totals.get('03', 0.0)   # ICA

            company = move.company_id
            journal = move.journal_id
            edi_datetime = move.l10n_co_edi_datetime or fields.Datetime.now()

            # Determine subtotal (base amount before taxes)
            subtotal = abs(move.amount_untaxed_signed)
            total = abs(move.amount_total_signed)

            nit_ofe = (company.vat or '').replace('-', '').strip()
            partner = move.commercial_partner_id
            num_adq = (partner.vat or partner.l10n_latam_identification_type_id.name or '').replace('-', '').strip()

            tipo_ambiente = '2' if company.l10n_co_edi_test_mode else '1'

            if move.move_type == 'out_invoice':
                # CUFE for sales invoices — uses technical key
                cl_tec = journal.l10n_co_edi_dian_technical_key or ''
                cufe = compute_cufe(
                    num_fac=move.name or '',
                    fec_fac=edi_datetime,
                    val_fac=subtotal,
                    cod_imp_1='01',
                    val_imp_1=iva_amount,
                    cod_imp_2='04',
                    val_imp_2=inc_amount,
                    cod_imp_3='03',
                    val_imp_3=ica_amount,
                    val_tot=total,
                    nit_ofe=nit_ofe,
                    num_adq=num_adq,
                    cl_tec=cl_tec,
                    tipo_ambiente=tipo_ambiente,
                )
                move.l10n_co_edi_cufe_cude = cufe
            elif move.move_type in ('out_refund', 'in_refund'):
                # CUDE for credit/debit notes — uses software PIN
                pin_software = company.l10n_co_edi_software_pin or ''
                cude = compute_cude(
                    num_doc=move.name or '',
                    fec_doc=edi_datetime,
                    val_doc=subtotal,
                    cod_imp_1='01',
                    val_imp_1=iva_amount,
                    cod_imp_2='04',
                    val_imp_2=inc_amount,
                    cod_imp_3='03',
                    val_imp_3=ica_amount,
                    val_tot=total,
                    nit_ofe=nit_ofe,
                    num_adq=num_adq,
                    pin_software=pin_software,
                    tipo_ambiente=tipo_ambiente,
                )
                move.l10n_co_edi_cufe_cude = cude

            # Build QR data
            if move.l10n_co_edi_cufe_cude:
                move.l10n_co_edi_qr_data = (
                    'https://catalogo-vpfe.dian.gov.co/document/searchqr?documentkey=%s'
                    % move.l10n_co_edi_cufe_cude
                )

    def _l10n_co_edi_get_tax_totals_by_type(self):
        """Aggregate tax amounts by DIAN tax type code.

        Returns a dict like {'01': 1900.00, '03': 0.00, '04': 0.00}
        where keys are DIAN tax type codes.
        """
        self.ensure_one()
        result = {}
        for line in self.line_ids.filtered(lambda l: l.tax_line_id):
            tax = line.tax_line_id
            # Look up the DIAN tax type code from the tax group name
            dian_code = self._l10n_co_edi_get_dian_tax_code(tax)
            if dian_code:
                result[dian_code] = result.get(dian_code, 0.0) + abs(line.balance)
        return result

    @api.model
    def _l10n_co_edi_cron_poll_dian_status(self):
        """Cron job: poll DIAN for status of pending/sent invoices.

        Finds all Colombian invoices in 'pending' or 'sent' state and
        queries DIAN for their current status.
        """
        pending_moves = self.search([
            ('l10n_co_edi_state', 'in', ('pending', 'sent')),
            ('l10n_co_edi_cufe_cude', '!=', False),
            ('company_id.account_fiscal_country_id.code', '=', 'CO'),
        ], limit=50)  # Process in batches

        if not pending_moves:
            return

        import logging
        _logger = logging.getLogger(__name__)
        dian_client = self.env['l10n_co_edi.dian.client']

        for move in pending_moves:
            try:
                company = move.company_id
                track_id = move.l10n_co_edi_cufe_cude

                response = dian_client._get_status(company, track_id)
                if not response:
                    continue

                if dian_client._is_dian_response_success(response):
                    move.l10n_co_edi_state = 'validated'
                    move.l10n_co_edi_dian_response = response.get('application_response', '')
                    move.l10n_co_edi_dian_response_status = str(response.get('status_code', ''))
                    _logger.info('Invoice %s: DIAN validated successfully.', move.name)
                elif response.get('status_code') is not None:
                    # Got a definitive response — check if it's a rejection
                    errors = response.get('errors', [])
                    if errors:
                        move.l10n_co_edi_state = 'rejected'
                        move.l10n_co_edi_dian_response = response.get('raw_response', '')
                        move.l10n_co_edi_dian_response_status = str(response.get('status_code', ''))
                        error_msg = dian_client._format_dian_error(response)
                        _logger.warning('Invoice %s: DIAN rejected: %s', move.name, error_msg)
                    else:
                        # Still processing — update state to 'sent' if it was 'pending'
                        if move.l10n_co_edi_state == 'pending':
                            move.l10n_co_edi_state = 'sent'

            except Exception as e:
                _logger.warning(
                    'Invoice %s: Error polling DIAN status: %s',
                    move.name, str(e),
                )

    @api.model
    def _l10n_co_edi_get_dian_tax_code(self, tax):
        """Map a Colombian tax to its DIAN tax type code.

        The mapping is based on the tax group name prefix:
        - IVA -> 01
        - INC -> 04
        - ICA / R ICA -> 03
        - RteFte / R REN -> 06
        - RteIVA / R IVA -> 05
        """
        if not tax or not tax.tax_group_id:
            return None
        group_name = (tax.tax_group_id.name or '').upper()
        if group_name.startswith('IVA') or group_name.startswith('R IVA'):
            return '01'
        if group_name.startswith('INC'):
            return '04'
        if group_name.startswith('ICA') or group_name.startswith('R ICA'):
            return '03'
        if group_name.startswith('R REN') or group_name.startswith('RTEFTE'):
            return '06'
        return None
