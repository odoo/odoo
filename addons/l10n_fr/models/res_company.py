from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_fr_config_id = fields.Many2one(
        comodel_name="l10n_fr.config",
        compute="_compute_l10n_fr_config_id",
        search="_search_l10n_fr_config_id",
    )

    ape = fields.Char(
        related="l10n_fr_config_id.ape",
        readonly=False,
    )

    is_france_country = fields.Boolean(
        related="l10n_fr_config_id.is_france_country",
    )

    def _search_l10n_fr_config_id(self, operator, value):
        return self._search_config_link("l10n_fr.config", operator, value)

    def _compute_l10n_fr_config_id(self):
        configs = self.env["l10n_fr.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_fr_config_id = by_company.get(company.id, False)

    @api.model
    def _get_france_country_codes(self):
        """Returns every country code that can be used to represent France"""
        return [
            "FR",
            "MF",
            "MQ",
            "NC",
            "PF",
            "RE",
            "GF",
            "GP",
            "TF",
            "BL",
            "PM",
            "YT",
            "WF",
        ]  # These codes correspond to France and DOM-TOM.

    def _is_accounting_unalterable(self):
        if not self.vat and not self.country_id:
            return False
        return (
            self.country_id and self.country_id.code in self._get_france_country_codes()
        )

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company in companies:
            # when creating a new french company, create the securisation sequence as well
            if company._is_accounting_unalterable():
                sequence_fields = ["l10n_fr_closing_sequence_id"]
                company._create_secure_sequence(sequence_fields)
        return companies

    def write(self, vals):
        res = super().write(vals)
        # if country changed to fr, create the securisation sequence
        for company in self:
            if company._is_accounting_unalterable():
                sequence_fields = ["l10n_fr_closing_sequence_id"]
                company._create_secure_sequence(sequence_fields)
        return res

    def _create_secure_sequence(self, sequence_fields):
        """This function creates a no_gap sequence on each company in self that will ensure
        a unique number is given to all posted account.move in such a way that we can always
        find the previous move of a journal entry on a specific journal.
        """
        for company in self:
            vals_write = {}
            for seq_field in sequence_fields:
                if not company._config_owner_of(seq_field)[seq_field]:
                    vals = {
                        "name": self.env._(
                            "Securisation of %(field)s - %(company)s",
                            field=seq_field,
                            company=company.name,
                        ),
                        "code": "FRSECURE%s-%s" % (company.id, seq_field),
                        "implementation": "no_gap",
                        "prefix": "",
                        "suffix": "",
                        "padding": 0,
                        "company_id": company.id,
                    }
                    seq = self.env["ir.sequence"].create(vals)
                    vals_write[seq_field] = seq.id
            if vals_write:
                company.write(vals_write)  # routed to the owning configuration
