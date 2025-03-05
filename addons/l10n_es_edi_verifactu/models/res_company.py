from odoo import _, api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_es_edi_verifactu_certificate_ids = fields.One2many(
        comodel_name='l10n_es_edi_verifactu.certificate',
        inverse_name='company_id',
    )
    l10n_es_edi_verifactu_required = fields.Boolean(
        string="Enable Veri*Factu",
        default=False,
    )
    l10n_es_edi_verifactu_test_environment = fields.Boolean(
        string="Veri*Factu Test Environment",
        default=True,
    )
    l10n_es_edi_verifactu_last_record_document_id = fields.Many2one(
        string='Last Veri*Factu Record',
        comodel_name='l10n_es_edi_verifactu.record_document',
        readonly=True,
        help="Last succesfully generated Veri*Factu Record."
    )

    def _l10n_es_edi_verifactu_get_endpoints(self):
        """
        For the SOAP endpoints see:
        https://prewww2.aeat.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/SistemaFacturacion.wsdl
        """
        self.ensure_one()
        TEST_ENDPOINT = "https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP"
        QR_TEST_ENDPOINT = "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR"
        if self.l10n_es_edi_verifactu_test_environment:
            endpoints = {
                'verifactu': TEST_ENDPOINT,
                'QR': QR_TEST_ENDPOINT
            }
        else:
            # TODO: update when production endpoints are released
            endpoints = {
                'verifactu': TEST_ENDPOINT,
                'QR': QR_TEST_ENDPOINT
            }
        return endpoints

    def _l10n_es_edi_verifactu_get_values(self):
        self.ensure_one()
        errors = []
        name = self.name[:120]
        nif = self.vat[2:] if self.vat and self.vat.startswith('ES') else self.vat
        return {
            'name': name,
            'NIF': nif,
            'errors': errors,
        }

    def _l10n_es_edi_verifactu_get_certificate(self):
        self.ensure_one()
        return self.env['l10n_es_edi_verifactu.certificate'].search(
            [('company_id', '=', self.id)],
            order='date_end desc',
            limit=1,
        )
