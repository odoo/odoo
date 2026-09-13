from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountTaxUnit(models.Model):
    _name = "account.tax.unit"
    _description = "Tax Unit"

    name = fields.Char(required=True)
    country_id = fields.Many2one(
        comodel_name="res.country",
        inverse="_inverse_vat_and_country_id",
        required=True,
        help="The country in which this tax unit is used to group your companies' tax reports declaration.",
    )
    vat = fields.Char(
        string="Tax ID",
        inverse="_inverse_vat_and_country_id",
        required=True,
        help="The identifier to be used when submitting a report for this unit.",
    )
    company_ids = fields.Many2many(
        comodel_name="res.company",
        string="Companies",
        required=True,
        help="Members of this unit",
    )
    main_company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        help="Main company of this unit; the one actually reporting and paying the taxes.",
    )
    fpos_synced = fields.Boolean(
        string="Fiscal Positions Synchronised",
        compute="_compute_fpos_synced",
        help="Technical field indicating whether Fiscal Positions exist for all companies in the unit",
    )

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
        res = super().create(vals_list)

        horizontal_groups = self.env["account.report.horizontal.group"].create(
            [
                {
                    "name": tax_unit.name,
                    "rule_ids": [
                        Command.create(
                            {
                                "field_name": "company_id",
                                "domain": f"[('account_tax_unit_ids', 'in', {tax_unit.id})]",
                            }
                        ),
                    ],
                }
                for tax_unit in res
            ]
        )

        _debug.pipeline(
            "tax_unit_horizontal_groups_created",
            tax_units=res,
            horizontal_groups=horizontal_groups,
        )
        generic_tax_report = self.env.ref("account.generic_tax_report")
        generic_tax_report.horizontal_group_ids |= horizontal_groups

        generic_tax_report_account_tax = self.env.ref(
            "account.generic_tax_report_account_tax"
        )
        generic_tax_report_account_tax.horizontal_group_ids |= horizontal_groups

        generic_tax_report_tax_account = self.env.ref(
            "account.generic_tax_report_tax_account"
        )
        generic_tax_report_tax_account.horizontal_group_ids |= horizontal_groups

        generic_ec_sales_report = self.env.ref("account.generic_ec_sales_report")
        generic_ec_sales_report.horizontal_group_ids |= horizontal_groups

        for tax_unit in res:
            generic_tax_report.variant_report_ids.filtered(
                lambda variant, tax_unit=tax_unit: (
                    variant.country_id == tax_unit.country_id
                )
            ).write(
                {
                    "horizontal_group_ids": [
                        Command.link(group.id) for group in horizontal_groups
                    ],
                }
            )

        _debug.pipeline(
            "tax_unit_returns_sync",
            tax_units=res,
            report=generic_tax_report,
        )
        self.env["account.return.type"]._sync_all_returns(res.company_ids.root_id)
        return res

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        root_companies_before = self.company_ids.root_id
        result = super().write(vals)
        if any(
            return_field in vals
            for return_field in ("main_company_id", "company_ids", "country_id")
        ):
            self.env["account.return.type"]._sync_all_returns(
                root_companies_before | self.company_ids.root_id
            )
        return result

    @api.depends("company_ids")
    @_debug.perf.timed
    def _compute_fpos_synced(self):
        # The real input is every company partner's property_account_position_id, which
        # no @api.depends can reach: it is company-dependent, on arbitrary partners.
        # Whatever writes those positions has to invalidate this field -- see
        # action_sync_unit_fiscal_positions.
        all_companies = self.env["res.company"].search([])
        for unit in self:
            synced = True
            for company in unit.company_ids:
                origin_company = company._origin
                fp = unit._get_tax_unit_fiscal_positions(companies=origin_company)
                all_partners_with_fp = (
                    all_companies.with_company(origin_company).partner_id.filtered(
                        lambda p, fp=fp: p.property_account_position_id == fp
                    )
                    if fp
                    else self.env["res.partner"]
                )
                synced = (
                    all_partners_with_fp
                    == (unit.company_ids - origin_company).partner_id
                )
                if not synced:
                    break
            unit.fpos_synced = synced

    def _get_tax_unit_fiscal_positions(self, companies, create_or_refresh=False):
        """Retrieve or create fiscal positions for all companies specified.

        :param companies: companies for which to find/create fiscal positions
        :param create_or_refresh: whether the fiscal positions should be created if not found
        :return: all the fiscal positions found/created for the companies requested
        :rtype: recordset of account.fiscal.position
        """
        # These fiscal positions have no taxes, so this could probably be simplified
        # (as refresh makes no sense anymore).
        fiscal_positions = self.env["account.fiscal.position"].with_context(
            allowed_company_ids=self.env.user.company_ids.ids
        )
        for unit in self:
            for company in companies:
                fp_identifier = "account.tax_unit_%s_fp_%s" % (unit.id, company.id)
                existing_fp = self.env.ref(fp_identifier, raise_if_not_found=False)
                if create_or_refresh:
                    data = {
                        "xml_id": fp_identifier,
                        "values": {
                            "name": unit.name,
                            "company_id": company.id,
                        },
                    }
                    existing_fp = fiscal_positions._load_records([data])
                if existing_fp:
                    fiscal_positions += existing_fp
        _debug.pipeline(
            "unit_fiscal_positions_resolved",
            units=self,
            companies=companies,
            create_or_refresh=create_or_refresh,
            fiscal_positions=fiscal_positions,
        )
        return fiscal_positions

    @_debug.perf.timed
    def action_sync_unit_fiscal_positions(self):
        _debug.lifecycle("action_sync_unit_fiscal_positions", records=self)
        self._get_tax_unit_fiscal_positions(
            companies=self.env["res.company"].search([])
        ).unlink()
        for unit in self:
            for company in unit.company_ids:
                fp = unit._get_tax_unit_fiscal_positions(
                    companies=company, create_or_refresh=True
                )
                (unit.company_ids - company).with_company(
                    company
                ).partner_id.property_account_position_id = fp

        # fpos_synced reads the positions just written, and depends on company_ids alone,
        # so without this the flag keeps the value it had before the sync ran.
        self.invalidate_recordset(["fpos_synced"])

    @_debug.perf.timed
    def unlink(self):
        # EXTENDS base
        _debug.lifecycle("unlink", unlink=self)
        self._get_tax_unit_fiscal_positions(
            companies=self.env["res.company"].search([])
        ).unlink()
        return super().unlink()

    @api.constrains("country_id", "company_ids")
    @_debug.perf.timed
    def _check_companies_country(self):
        for record in self:
            currencies = set()
            for company in record.company_ids:
                currencies.add(company.currency_id)

                if any(
                    unit != record and unit.country_id == record.country_id
                    for unit in company.account_tax_unit_ids
                ):
                    _debug.logic(
                        "tax_unit_company_conflict",
                        unit=record,
                        company=company,
                        reason="company_in_same_country_unit",
                    )
                    raise ValidationError(
                        _(
                            "Company %(company)s already belongs to a tax unit in %(country)s. A company can at most be part of one tax unit per country.",
                            company=company.name,
                            country=record.country_id.name,
                        )
                    )

            if len(currencies) > 1:
                _debug.logic(
                    "tax_unit_currency_mismatch",
                    unit=record,
                    currencies=len(currencies),
                )
                raise ValidationError(
                    _(
                        "A tax unit can only be created between companies sharing the same main currency."
                    )
                )

    @api.constrains("company_ids", "main_company_id")
    @_debug.perf.timed
    def _check_main_company(self):
        for record in self:
            if record.main_company_id not in record.company_ids:
                raise ValidationError(
                    _("The main company of a tax unit has to be part of it.")
                )

    @api.constrains("company_ids")
    @_debug.perf.timed
    def _check_company_ids(self):
        for record in self:
            if len(record.company_ids) < 2:
                raise ValidationError(
                    _(
                        "A tax unit must contain a minimum of two companies. You might want to delete the unit."
                    )
                )

    @api.onchange("vat", "country_id")
    def _onchange_vat(self):
        self.vat, _country_code = self.env["res.partner"]._run_vat_checks(
            self.country_id, self.vat, validation=False
        )

    @_debug.perf.timed
    def _inverse_vat_and_country_id(self):
        for record in self:
            if not record.vat:
                continue

            _vat, checked_country_code = self.env["res.partner"]._run_vat_checks(
                record.country_id,
                record.vat,
                partner_name=_("tax unit [%s]", record.name),
            )
            if checked_country_code and checked_country_code != record.country_id.code:
                _debug.logic(
                    "tax_unit_vat_country_mismatch",
                    unit=record,
                    detected_country=checked_country_code,
                )
                raise ValidationError(
                    _(
                        "The country detected for this VAT number does not match the one set on this Tax Unit."
                    )
                )

    @api.onchange("company_ids")
    def _onchange_company_ids(self):
        if self.main_company_id not in self.company_ids and self.company_ids:
            self.main_company_id = self.company_ids[0]._origin
        elif not self.company_ids:
            self.main_company_id = False
