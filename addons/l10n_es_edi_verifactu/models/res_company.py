from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_es_edi_verifactu_config_id = fields.Many2one(
        comodel_name="l10n_es_edi_verifactu.config",
        compute="_compute_l10n_es_edi_verifactu_config_id",
        search="_search_l10n_es_edi_verifactu_config_id",
    )

    l10n_es_edi_verifactu_required = fields.Boolean(
        related="l10n_es_edi_verifactu_config_id.l10n_es_edi_verifactu_required",
    )

    # the company's own certificates, whose inverse names the company: a
    # collection it owns, not a setting the configuration keeps
    l10n_es_edi_verifactu_certificate_ids = fields.One2many(
        comodel_name="certificate.certificate",
        inverse_name="company_id",
        string="Veri*Factu Certificates",
    )

    l10n_es_edi_verifactu_special_vat_regime = fields.Selection(
        related="l10n_es_edi_verifactu_config_id.l10n_es_edi_verifactu_special_vat_regime",
        readonly=False,
    )

    def _search_l10n_es_edi_verifactu_config_id(self, operator, value):
        return self._search_config_link("l10n_es_edi_verifactu.config", operator, value)

    def _compute_l10n_es_edi_verifactu_config_id(self):
        configs = self.env["l10n_es_edi_verifactu.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_es_edi_verifactu_config_id = by_company.get(company.id, False)

    def _l10n_es_edi_verifactu_get_endpoints(self):
        """
        For the SOAP endpoints see:
        https://prewww2.aeat.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/SistemaFacturacion.wsdl
        """
        self.check_singleton()
        wsdl_base = {
            "url": "https://prewww2.aeat.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/SistemaFacturacion.wsdl",
            "service": "sfVerifactu",
            "registration": "RegFactuSistemaFacturacion",
            "port": None,
        }
        if self.l10n_es_edi_verifactu_config_id.l10n_es_edi_verifactu_test_environment:
            endpoints = {
                "wsdl": wsdl_base | {"port": "SistemaVerifactuPruebas"},
                "verifactu": "https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP",
                "QR": "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR",
            }
        else:
            endpoints = {
                "wsdl": wsdl_base | {"port": "SistemaVerifactu"},
                "verifactu": "https://www1.agenciatributaria.gob.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP",
                "QR": "https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR",
            }
        return endpoints

    def _l10n_es_edi_verifactu_get_certificate(self):
        self.check_singleton()
        return self.env["certificate.certificate"].search(
            [("company_id", "=", self.id), ("scope", "=", "verifactu")],
            order="date_end desc",
            limit=1,
        )

    def _l10n_es_edi_verifactu_get_chain_sequence(self):
        self.check_singleton()
        if not self.l10n_es_edi_verifactu_config_id.l10n_es_edi_verifactu_chain_sequence_id:
            self_sudo = self.sudo()
            self_sudo.l10n_es_edi_verifactu_config_id.l10n_es_edi_verifactu_chain_sequence_id = self_sudo.env[
                "ir.sequence"
            ].create(
                {
                    "name": self.env._(
                        "Veri*Factu Document Sequence for company %(name)s (%(id)s)",
                        name=self.name,
                        id=self.id,
                    ),
                    "code": f"l10n_es_edi_verifactu.document.{self.id}",
                    "implementation": "no_gap",
                    "company_id": self.id,
                }
            )
        return (
            self.l10n_es_edi_verifactu_config_id.l10n_es_edi_verifactu_chain_sequence_id
        )

    def _l10n_es_edi_verifactu_get_last_document(self):
        self.check_singleton()
        return self.env["l10n_es_edi_verifactu.document"].search(
            [
                ("chain_index", "!=", False),
                ("company_id", "=", self.id),
            ],
            order="chain_index DESC",
            limit=1,
        )
