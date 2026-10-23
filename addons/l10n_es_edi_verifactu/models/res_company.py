from odoo import _, fields, models
from odoo.addons.l10n_es_edi_verifactu.const import VERIFACTU_REGIME_CODES_IGIC, VERIFACTU_REGIME_CODES_IVA
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_es_edi_verifactu_certificate_ids = fields.One2many(
        string="Veri*Factu Certificates",
        comodel_name='certificate.certificate',
        inverse_name='company_id',
    )
    l10n_es_edi_verifactu_required = fields.Boolean(
        string="Enable Veri*Factu",
        copy=False,
    )
    l10n_es_edi_verifactu_test_environment = fields.Boolean(
        string="Veri*Factu Test Environment",
        default=True,
        copy=False,
    )

    def write(self, vals):
        if 'l10n_es_edi_verifactu_test_environment' not in vals:
            return super().write(vals)

        to_test_env = bool(vals['l10n_es_edi_verifactu_test_environment'])
        changed = self.filtered(lambda c: c.l10n_es_edi_verifactu_test_environment != to_test_env)
        if to_test_env:
            blocked = self.env['l10n_es_edi_verifactu.issuer'].sudo().search_count([
                ('company_id', 'in', changed.ids),
                ('chain_sequence_id', '!=', False),
            ], limit=1)
            message = _("Documents have already been chained in the Veri*Factu production environment; the test environment cannot be enabled again. Use a duplicated database to run tests.")
        else:
            blocked = self.env['l10n_es_edi_verifactu.document'].sudo().search_count([
                ('company_id', 'in', changed.ids),
                ('json_attachment_id', '!=', False),
                ('state', '=', False),
            ], limit=1)
            message = _("Some Veri*Factu documents generated in the test environment are still waiting to be sent. Send them before switching to production.")
        if blocked:
            raise UserError(message)
        res = super().write(vals)
        if not to_test_env and changed:
            # Restart the chain: the next document gets a new sequence and 'PrimerRegistro'
            self.env['l10n_es_edi_verifactu.issuer'].sudo().search([
                ('company_id', 'in', changed.ids),
            ]).chain_sequence_id = False
        return res

    def _l10n_es_edi_verifactu_get_endpoints(self):
        """
        For the SOAP endpoints see:
        https://prewww2.aeat.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/SistemaFacturacion.wsdl
        """
        self.ensure_one()
        wsdl_base = {
            'url': 'https://prewww2.aeat.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/SistemaFacturacion.wsdl',
            'service': 'sfVerifactu',
            'registration': 'RegFactuSistemaFacturacion',
            'port': None,
        }
        if self.l10n_es_edi_verifactu_test_environment:
            endpoints = {
                'wsdl': wsdl_base | {'port': 'SistemaVerifactuPruebas'},
                'verifactu': 'https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP',
                'QR': 'https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR',
            }
        else:
            endpoints = {
                'wsdl': wsdl_base | {'port': 'SistemaVerifactu'},
                'verifactu': 'https://www1.agenciatributaria.gob.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP',
                'QR': 'https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR'
            }
        return endpoints

    def _l10n_es_edi_verifactu_get_certificate(self):
        self.ensure_one()
        return self.env['certificate.certificate'].search(
            [('company_id', '=', self.id), ('scope', '=', 'verifactu')],
            order='date_end desc',
            limit=1,
        )

    def _l10n_es_regime_available_codes(self, use, applicability=None):
        # EXTENDS 'l10n_es'
        self.ensure_one()
        # VeriFactu only applies to sale taxes; purchase taxes always fall back to the
        # generic catalog, even on a VeriFactu company.
        if self.l10n_es_edi_verifactu_required and use == 'sale':
            if applicability == '03':  # IGIC
                return VERIFACTU_REGIME_CODES_IGIC
            return VERIFACTU_REGIME_CODES_IVA  # IVA ('01'), IPSI ('02') and unset/"Other" default here
        return super()._l10n_es_regime_available_codes(use, applicability=applicability)
