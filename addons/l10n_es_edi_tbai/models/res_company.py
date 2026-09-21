import re

from odoo import fields, models, release
from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)
L10N_ES_TBAI_LICENSE_DICT = {
    "production": {
        "license_name": _lt("Production license"),  # all agencies
        "license_number": "TBAIGI5A266A7CCDE1EC",
        "license_nif": "N0251909H",
        "software_name": "Odoo SA",
        "software_version": release.version,
    },
    "araba": {
        "license_name": _lt("Test license (Araba)"),
        "license_number": "TBAIARbjjMClHKH00849",
        "license_nif": "N0251909H",
        "software_name": "Odoo SA",
        "software_version": release.version,
    },
    "bizkaia": {
        "license_name": _lt("Test license (Bizkaia)"),
        "license_number": "TBAIBI00000000PRUEBA",
        "license_nif": "A99800005",
        "software_name": "SOFTWARE GARANTE TICKETBAI PRUEBA",
        "software_version": "1.0",
    },
    "gipuzkoa": {
        "license_name": _lt("Test license (Gipuzkoa)"),
        "license_number": "TBAIGIPRE00000000965",
        "license_nif": "N0251909H",
        "software_name": "Odoo SA",
        "software_version": release.version,
    },
}


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_es_edi_tbai_config_id = fields.Many2one(
        comodel_name="l10n_es_edi_tbai.config",
        compute="_compute_l10n_es_edi_tbai_config_id",
        search="_search_l10n_es_edi_tbai_config_id",
    )

    l10n_es_tbai_is_enabled = fields.Boolean(
        related="l10n_es_edi_tbai_config_id.l10n_es_tbai_is_enabled",
    )

    # the company form shows the licence, so the company declares it
    l10n_es_tbai_license_html = fields.Html(
        related="l10n_es_edi_tbai_config_id.l10n_es_tbai_license_html",
    )

    # the company's own certificates, whose inverse names the company: a
    # collection it owns, not a setting the configuration keeps
    l10n_es_tbai_certificate_ids = fields.One2many(
        comodel_name="certificate.certificate",
        inverse_name="company_id",
        domain=[("scope", "=", "tbai")],
    )

    def _search_l10n_es_edi_tbai_config_id(self, operator, value):
        return self._search_config_link("l10n_es_edi_tbai.config", operator, value)

    def _compute_l10n_es_edi_tbai_config_id(self):
        configs = self.env["l10n_es_edi_tbai.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_es_edi_tbai_config_id = by_company.get(company.id, False)

    def _get_l10n_es_tbai_license_dict(self):
        self.check_singleton()
        if self.l10n_es_edi_tbai_config_id.l10n_es_tbai_is_enabled:
            if (
                self.l10n_es_edi_tbai_config_id.l10n_es_tbai_test_env
            ):  # test env: each agency has its test license
                license_key = self.l10n_es_edi_tbai_config_id.l10n_es_tbai_tax_agency
            else:  # production env: only one license
                license_key = "production"
            license = L10N_ES_TBAI_LICENSE_DICT[license_key]
            return dict(
                license, license_name=str(license["license_name"])
            )  # force translation
        else:
            return {}

    def _get_l10n_es_tbai_next_chain_index(self):
        if not self.l10n_es_edi_tbai_config_id.l10n_es_tbai_chain_sequence_id:
            self_sudo = self.sudo()
            self_sudo.l10n_es_edi_tbai_config_id.l10n_es_tbai_chain_sequence_id = self_sudo.env[
                "ir.sequence"
            ].create(
                {
                    "name": f"TicketBAI account move sequence for {self.name} (id: {self.id})",
                    "code": f"l10n_es.edi.tbai.account.move.{self.id}",
                    "implementation": "no_gap",
                    "company_id": self.id,
                }
            )
        return (
            self.l10n_es_edi_tbai_config_id.l10n_es_tbai_chain_sequence_id.next_by_id()
        )

    def _get_l10n_es_tbai_last_chained_document(self):
        """
        Returns the last tbai document posted to this company's chain.
        That tbai document may have been received by the govt or not (eg. in case of a timeout).
        Only upon confirmed reception/refusal of that tbai document can another one be posted.
        """
        domain = [("chain_index", "!=", 0), ("company_id", "=", self.id)]
        return self.env["l10n_es_edi_tbai.document"].search(
            domain, limit=1, order="chain_index desc"
        )

    def _l10n_es_freelancer(self):
        self.check_singleton()
        return (
            self.vat and re.fullmatch(r"(ES)?(\d{8}[A-Z]|[X-Z].*)", self.vat)
        ) or False
