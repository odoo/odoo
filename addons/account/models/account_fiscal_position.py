from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import unique

_debug = DebugLog(__name__)


class AccountFiscalPosition(models.Model):
    _name = "account.fiscal.position"
    _description = "Fiscal Position"
    _order = "sequence"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char(
        string="Fiscal Position",
        translate=True,
        required=True,
    )
    active = fields.Boolean(
        default=True,
        help="By unchecking the active field, you may hide a fiscal position without deleting it.",
    )
    sequence = fields.Integer()
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        readonly=True,
        required=True,
    )
    account_ids = fields.One2many(
        comodel_name="account.fiscal.position.account",
        inverse_name="position_id",
        string="Account Mapping",
        copy=True,
    )
    account_map = fields.Binary(compute="_compute_account_map")
    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        relation="account_fiscal_position_account_tax_rel",
        column1="account_fiscal_position_id",
        column2="account_tax_id",
        string="Taxes",
    )
    tax_map = fields.Binary(compute="_compute_tax_map")
    note = fields.Html(
        string="Notes",
        translate=True,
        help="Legal mentions that have to be printed on the invoices.",
    )
    auto_apply = fields.Boolean(
        string="Detect Automatically",
        help="Apply tax & account mappings on invoices automatically if the matching criterias (VAT/Country) are met.",
    )
    vat_required = fields.Boolean(
        string="VAT required",
        help="Apply only if partner has a VAT number.",
    )
    company_country_id = fields.Many2one(
        related="company_id.account_config_id.account_fiscal_country_id",
        string="Company Country",
    )
    fiscal_country_codes = fields.Char(
        related="company_country_id.code",
        string="Company Fiscal Country Code",
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        inverse="_inverse_vat_territory",
        help="Apply only if delivery country matches.",
    )
    is_domestic = fields.Boolean(
        compute="_compute_is_domestic",
        store=True,
    )
    country_group_id = fields.Many2one(
        comodel_name="res.country.group",
        inverse="_inverse_vat_territory",
        help="Apply only if delivery country matches the group.",
    )
    state_ids = fields.Many2many(
        comodel_name="res.country.state",
        string="Federal States",
    )
    zip_from = fields.Char(string="Zip Range From")
    zip_to = fields.Char(string="Zip Range To")
    states_count = fields.Integer(compute="_compute_states_count")
    foreign_vat = fields.Char(
        string="Foreign Tax ID",
        inverse="_inverse_vat_territory",
        help="The tax ID of your company in the region mapped by this fiscal position.",
    )

    foreign_vat_header_mode = fields.Selection(
        selection=[
            ("templates_found", "Templates Found"),
            ("no_template", "No Template"),
        ],
        compute="_compute_foreign_vat_header_mode",
    )

    @api.constrains("zip_from", "zip_to")
    @_debug.perf.timed
    def _check_zip(self):
        for position in self:
            if (
                bool(position.zip_from) != bool(position.zip_to)
                or position.zip_from > position.zip_to
            ):
                raise ValidationError(
                    _(
                        'Invalid "Zip Range", You have to configure both "From" and "To" values for the zip range and "To" should be greater than "From".'
                    )
                )

    @api.constrains("country_id", "country_group_id", "state_ids", "foreign_vat")
    @_debug.perf.timed
    def _check_foreign_vat_country(self):
        foreign_vat_positions = self.search(
            [
                *self._check_company_domain(self.company_id),
                ("foreign_vat", "!=", False),
                ("country_id", "in", self.country_id.ids),
            ]
        )
        _debug.pipeline(
            "foreign_vat_candidates", positions=self, candidates=foreign_vat_positions
        )
        for record in self:
            if not record.foreign_vat:
                continue

            if not record.country_id:
                raise ValidationError(
                    _(
                        "The country of the foreign VAT number could not be detected. Please assign a country to the fiscal position."
                    )
                )

            fiscal_country = (
                record.company_id.account_config_id.account_fiscal_country_id
            )
            if (
                record.country_id == fiscal_country
                and not record.state_ids
                and fiscal_country.state_ids
            ):
                _debug.logic(
                    "foreign_vat_rejected", fpos=record, reason="domestic_no_state"
                )
                raise ValidationError(
                    _(
                        "You cannot create a fiscal position with a foreign VAT within your fiscal country without assigning it a state."
                    )
                )

            if (
                record.country_group_id
                and record.country_id not in record.country_group_id.country_ids
            ):
                raise ValidationError(
                    _(
                        "You cannot create a fiscal position with a country outside of the selected country group."
                    )
                )

            if any(
                other.id != record.id
                and other.country_id == record.country_id
                and other.foreign_vat not in (False, record.foreign_vat)
                for other in foreign_vat_positions.filtered_domain(
                    record._check_company_domain(record.company_id)
                )
            ):
                _debug.logic(
                    "foreign_vat_rejected",
                    fpos=record,
                    reason="duplicate_in_country",
                )
                raise ValidationError(
                    _(
                        "A fiscal position with a foreign VAT already exists in this country."
                    )
                )
            _debug.logic("foreign_vat_accepted", fpos=record, country=record.country_id)

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        for vals in vals_list:
            zip_from = vals.get("zip_from")
            zip_to = vals.get("zip_to")
            if zip_from and zip_to:
                vals["zip_from"], vals["zip_to"] = self._convert_zip_values(
                    zip_from, zip_to
                )
        positions = super().create(vals_list)
        self._invalidate_company_configs()
        return positions

    @_debug.perf.timed
    def _invalidate_company_configs(self):
        # the configuration derives its positions from this model
        self.env["account.config"].invalidate_model(
            [
                "fiscal_position_ids",
                "domestic_fiscal_position_id",
                "multi_vat_foreign_country_ids",
                "account_enabled_tax_country_ids",
            ]
        )

    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        self._invalidate_company_configs()
        zip_from = vals.get("zip_from")
        zip_to = vals.get("zip_to")
        _debug.logic(
            "zip_write_mode",
            records=self,
            mode=(
                "untouched"
                if not (zip_from or zip_to)
                else "both"
                if zip_from and zip_to
                else "per_record"
            ),
        )
        if not (zip_from or zip_to):
            return super().write(vals)

        if zip_from and zip_to:
            padded_from, padded_to = self._convert_zip_values(zip_from, zip_to)
            return super().write({**vals, "zip_from": padded_from, "zip_to": padded_to})

        for rec in self:
            effective_from = zip_from if "zip_from" in vals else rec.zip_from
            effective_to = zip_to if "zip_to" in vals else rec.zip_to
            padded_from, padded_to = self._convert_zip_values(
                effective_from, effective_to
            )
            super(AccountFiscalPosition, rec).write(
                {**vals, "zip_from": padded_from, "zip_to": padded_to}
            )
        return True

    @api.depends("company_id.account_config_id.domestic_fiscal_position_id")
    def _compute_is_domestic(self):
        for position in self:
            position.is_domestic = (
                position
                == position.company_id.account_config_id.domestic_fiscal_position_id
            )

    @api.depends("country_id.state_ids")
    def _compute_states_count(self):
        for position in self:
            position.states_count = len(position.country_id.state_ids)

    @api.depends("foreign_vat", "country_id", "company_id")
    @_debug.perf.timed
    def _compute_foreign_vat_header_mode(self):
        AccountTax = self.env["account.tax"]
        country_taxes = AccountTax.search(
            [
                *AccountTax._check_company_domain(self.company_id),
                ("country_id", "in", self.country_id.ids),
            ]
        )
        for fiscal_position in self:
            if (
                not fiscal_position.foreign_vat
                or not fiscal_position.country_id
                or country_taxes.filtered(
                    lambda tax, fiscal_position=fiscal_position: (
                        tax.country_id == fiscal_position.country_id
                    )
                ).filtered_domain(
                    AccountTax._check_company_domain(fiscal_position.company_id)
                )
            ):
                fiscal_position.foreign_vat_header_mode = False
            else:
                template = self._get_foreign_tax_chart_template(
                    fiscal_position.country_id
                )
                fiscal_position.foreign_vat_header_mode = (
                    "templates_found" if template["installed"] else "no_template"
                )

    @api.depends("tax_ids")
    def _compute_tax_map(self):
        for position in self:
            tax_map = defaultdict(list)
            for dest_tax in position.tax_ids:
                for src_tax in dest_tax.original_tax_ids:
                    tax_map[src_tax.id].append(dest_tax.id)
            position.tax_map = dict(tax_map)

    @api.depends("account_ids.account_src_id", "account_ids.account_dest_id")
    def _compute_account_map(self):
        for position in self:
            position.account_map = {
                al.account_src_id.id: al.account_dest_id.id
                for al in position.account_ids
            }

    @api.onchange("country_id", "foreign_vat")
    def _onchange_foreign_vat(self):
        self.foreign_vat, _country_code = self.env["res.partner"]._run_vat_checks(
            self.country_id, self.foreign_vat, validation=False
        )

    @api.onchange("country_id")
    def _onchange_country_id(self):
        if self.country_id:
            self.zip_from = self.zip_to = False
            self.state_ids = [(5,)]
            self.states_count = len(self.country_id.state_ids)

    @api.onchange("country_group_id")
    def _onchange_country_group_id(self):
        if self.country_group_id:
            self.zip_from = self.zip_to = False
            self.state_ids = [(5,)]

    def _inverse_vat_territory(self):
        for record in self:
            if not record.foreign_vat:
                continue

            if record.country_id:
                fp_label = _("fiscal position [%s]", record.name)
                record.foreign_vat, _country_code = self.env[
                    "res.partner"
                ]._run_vat_checks(
                    record.country_id, record.foreign_vat, partner_name=fp_label
                )

    def _get_foreign_tax_chart_template(self, country):
        chart_template = self.env["account.chart.template"]
        template_code = chart_template._guess_chart_template(country)
        return chart_template._get_chart_template_mapping()[template_code]

    def _get_tax_country(self, company):
        if self.foreign_vat:
            return self.country_id
        return company.account_config_id.account_fiscal_country_id

    def map_tax(self, taxes):
        if not self:
            return taxes
        self.check_singleton()
        if not self.tax_ids:
            return taxes.filtered(lambda tax: not tax.fiscal_position_ids)
        tax_map = self.tax_map or {}
        return self.env["account.tax"].browse(
            unique(
                tax_id
                for tax in taxes
                for tax_id in tax_map.get(tax._origin.id or tax.id, [tax.id])
            )
        )

    def map_account(self, account):
        if not self:
            return account
        self.check_singleton()
        account_map = self.account_map or {}
        return self.env["account.account"].browse(
            account_map.get(account._origin.id or account.id, account.id)
        )

    @api.model
    def _convert_zip_values(self, zip_from="", zip_to=""):
        if zip_from and zip_to:
            max_length = max(len(zip_from), len(zip_to))
            if zip_from.isdigit():
                zip_from = zip_from.rjust(max_length, "0")
            if zip_to.isdigit():
                zip_to = zip_to.rjust(max_length, "0")
        return zip_from, zip_to

    def _get_first_matching_fpos(self, partner, company=None):
        sorted_fpos = self.sorted(
            key=lambda f: (-len(f.company_id.sudo().parent_ids), f.sequence)
        )
        validation_functions = self._get_fpos_validation_functions(partner, company)
        for fpos in sorted_fpos:
            if all(fn(fpos) for fn in validation_functions):
                return fpos
        return self.env["account.fiscal.position"]

    def _get_fpos_validation_functions(self, partner, company=None):
        company = company or self.env.company
        return [
            lambda fpos: (
                not fpos.vat_required or partner._is_vat_required_valid(company=company)
            ),
            lambda fpos: (
                not (fpos.zip_from and fpos.zip_to)
                or (partner.zip and (fpos.zip_from <= partner.zip <= fpos.zip_to))
            ),
            lambda fpos: not fpos.state_ids or (partner.state_id in fpos.state_ids),
            lambda fpos: not fpos.country_id or (partner.country_id == fpos.country_id),
            lambda fpos: (
                not fpos.country_group_id
                or (
                    partner.country_id in fpos.country_group_id.country_ids
                    and (
                        not partner.state_id
                        or partner.state_id
                        not in fpos.country_group_id.exclude_state_ids
                    )
                )
            ),
        ]

    @api.model
    @_debug.perf.timed
    def _get_fiscal_position(self, partner, delivery=None, company=None):
        if not partner:
            return self.env["account.fiscal.position"]

        company = company or self.env.company
        intra_eu = vat_exclusion = False
        if company.vat and partner.vat:
            eu_country_codes = set(
                self.env.ref("base.europe").country_ids.mapped("code")
            )
            intra_eu = (
                company.vat[:2] in eu_country_codes
                and partner.vat[:2] in eu_country_codes
            )
            vat_exclusion = company.vat[:2] == partner.vat[:2]

        if not delivery or (
            intra_eu and vat_exclusion and partner.country_id == company.country_id
        ):
            delivery = partner

        manual_fiscal_position = (
            delivery.with_company(company).property_account_position_id
            or partner.with_company(company).property_account_position_id
        )
        if manual_fiscal_position:
            _debug.logic(
                "fiscal_position_manual",
                partner=partner,
                manual_fiscal_position=manual_fiscal_position,
                intra_eu=intra_eu,
            )
            return manual_fiscal_position

        if not partner.country_id:
            _debug.logic("fiscal_position_no_country_none", partner=partner)
            return self.env["account.fiscal.position"]

        all_auto_apply_fpos = self.search(
            Domain(self._check_company_domain(company))
            & Domain("auto_apply", "=", True)
        )

        fpos = all_auto_apply_fpos._get_first_matching_fpos(delivery, company)
        _debug.logic(
            "fiscal_position_auto",
            partner=partner,
            fpos=fpos,
            all_auto_apply_fpos_count=len(all_auto_apply_fpos),
            delivery=delivery,
            intra_eu=intra_eu,
        )
        return fpos

    @_debug.perf.timed
    def action_view_related_taxes(self):
        _debug.lifecycle("action_view_related_taxes", records=self)
        list_view = self.env.ref(
            "account.account_tax_fiscal_position_view_tree", raise_if_not_found=False
        )
        domain = [
            *self.env["account.tax"]._check_company_domain(self.company_id),
            "|",
            ("id", "in", self.tax_ids.ids),
            ("fiscal_position_ids", "=", False),
        ]
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("%s taxes", self.display_name),
            "res_model": "account.tax",
            "views": [(list_view.id if list_view else False, "list"), (False, "form")],
            "domain": domain,
            "context": {"active_test": False},
        }

    @_debug.perf.timed
    def action_create_foreign_taxes(self):
        _debug.lifecycle("action_create_foreign_taxes", records=self)
        self.check_singleton()
        template = self._get_foreign_tax_chart_template(self.country_id)
        if not template["installed"]:
            localization_module = self.env["ir.module.module"].search(
                [("name", "=", template["module"])]
            )
            localization_module.sudo().button_immediate_install()
        created_records = self.env["account.chart.template"]._instantiate_foreign_taxes(
            self.country_id, self.company_id
        )
        created_records.get(
            "account.tax", self.env["account.tax"]
        ).fiscal_position_ids += self
