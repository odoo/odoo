# Part of GPCB. See LICENSE file for full copyright and licensing details.

"""CUNE (Codigo Unico de Nomina Electronica) computation.

The CUNE is a SHA-384 hash that uniquely identifies each electronic payroll
document, similar to CUFE/CUDE for invoices. Per DIAN Technical Annex for
Nomina Electronica:

    CUNE = SHA384(
        NumNomina + FechaGen + HoraGen + DevengadosTotal + DeduccionesTotal +
        NetoPagar + NIT_Empleador + NumDocEmpleado + TipoDoc + SoftwarePin + TipAmbiente
    )
"""

import hashlib
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class L10nCoPayrollCUNE(models.AbstractModel):
    _name = 'l10n_co.payroll.cune'
    _description = 'CUNE Computation Engine'

    @api.model
    def _compute_cune(self, document):
        """Compute the CUNE for an electronic payroll document.

        :param document: l10n_co.payroll.document record
        :return: CUNE hex string (SHA-384)
        """
        company = document.company_id
        employee = document.employee_id
        nit = (company.vat or '').replace('-', '').strip()
        emp_id = (employee.identification_id or '').replace('-', '').strip()

        # Software PIN from l10n_co_edi company settings
        software_pin = company.l10n_co_edi_software_pin or ''
        test_mode = getattr(company, 'l10n_co_edi_test_mode', False)
        ambiente = '2' if test_mode else '1'

        # Build the hash input string
        # NumNomina + FechaGen + HoraGen + DevengadosTotal + DeduccionesTotal +
        # NetoPagar + NIT + NumDoc + TipoDoc + PIN + Ambiente
        now = fields.Datetime.now()
        fecha_gen = (document.settlement_date or now.date()).isoformat()
        hora_gen = now.strftime('%H:%M:%S-05:00')  # Colombia UTC-5

        hash_input = ''.join([
            document.document_number or '',
            fecha_gen,
            hora_gen,
            f'{document.total_earnings:.2f}',
            f'{document.total_deductions:.2f}',
            f'{document.net_pay:.2f}',
            nit,
            emp_id,
            '102',  # Document type code (Nomina Individual)
            software_pin,
            ambiente,
        ])

        cune = hashlib.sha384(hash_input.encode()).hexdigest()
        _logger.debug(
            'CUNE for %s: hash_input=%s, cune=%s',
            document.document_number, hash_input, cune,
        )
        return cune

    @api.model
    def _verify_cune(self, document, expected_cune):
        """Verify a CUNE matches the expected value.

        :return: True if CUNE matches
        """
        computed = self._compute_cune(document)
        return computed == expected_cune
