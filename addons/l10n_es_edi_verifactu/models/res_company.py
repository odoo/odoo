from odoo import _, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_es_edi_verifactu_certificate_ids = fields.One2many(
        string="Veri*Factu Certificates",
        comodel_name='l10n_es_edi_verifactu.certificate',
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
    l10n_es_edi_verifactu_chain_sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string="Veri*Factu Document Chain Sequence",
        readonly=True,
        copy=False,
    )
    l10n_es_edi_verifactu_next_batch_time = fields.Datetime(
        string="Veri*Factu Next Batch Time",
        readonly=True,
        copy=False,
        help="The Datetime at which the next submission to the AEAT can be made.",
    )
    l10n_es_edi_verifactu_special_vat_regime = fields.Selection(
        string="Veri*Factu VAT Regime",
        selection=[
            ('simplified', "Simplified Regime"),
            ('reagyp', "REAGYP (Special Regime for Agriculture, Livestock and Fisheries)"),
            ('recargo', "Recargo de Equivalencia"),
        ],
        help="Leave empty for the normal regimen.",
    )

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
        return self.env['l10n_es_edi_verifactu.certificate'].search(
            [('company_id', '=', self.id)],
            order='date_end desc',
            limit=1,
        )

    def _l10n_es_edi_verifactu_get_chain_sequence(self):
        self.ensure_one()
        if not self.l10n_es_edi_verifactu_chain_sequence_id:
            self_sudo = self.sudo()
            self_sudo.l10n_es_edi_verifactu_chain_sequence_id = self_sudo.env['ir.sequence'].create({
                'name': _("Veri*Factu Document Sequence for company %(name)s (%(id)s)", name=self.name, id=self.id),
                'code': f'l10n_es_edi_verifactu.document.{self.id}',
                'implementation': 'no_gap',
                'company_id': self.id,
            })
        return self.l10n_es_edi_verifactu_chain_sequence_id

    def _l10n_es_edi_verifactu_get_last_document(self):
        self.ensure_one()
        return self.env['l10n_es_edi_verifactu.document'].search(
            [
                ('chain_index', '!=', False),
                ('company_id', '=', self.id),
            ],
            order='chain_index DESC',
            limit=1,
        )
