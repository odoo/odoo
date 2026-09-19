import ast
import json
from collections import defaultdict

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, frozendict

_debug = DebugLog(__name__)


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    tax_payable_account_id = fields.Many2one(
        comodel_name="account.account",
        check_company=True,
        help="Tax current account used as a counterpart to the Tax Closing Entry when in favor of the authorities.",
    )
    tax_receivable_account_id = fields.Many2one(
        comodel_name="account.account",
        check_company=True,
        help="Tax current account used as a counterpart to the Tax Closing Entry when in favor of the company.",
    )
    advance_tax_payment_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Tax Advance Account",
        check_company=True,
        help="Downpayments posted on this account will be considered by the Tax Closing Entry.",
    )


class AccountTax(models.Model):
    _name = "account.tax"
    _inherit = ["account.tax", "mixin.company.split"]

    fiscal_position_ids = fields.Many2many(
        comodel_name="account.fiscal.position",
        relation="account_fiscal_position_account_tax_rel",
        column1="account_tax_id",
        column2="account_fiscal_position_id",
    )
    original_tax_ids = fields.Many2many(
        comodel_name="account.tax",
        relation="account_tax_alternatives",
        column1="dest_tax_id",
        column2="src_tax_id",
        string="Replaces",
        domain="""[
            ('type_tax_use', '=', type_tax_use),
            ('is_domestic', '=', True),
        ]""",
        ondelete="cascade",
        help="List of taxes to replace when applying any of the stipulated fiscal positions.",
    )
    replacing_tax_ids = fields.Many2many(
        comodel_name="account.tax",
        relation="account_tax_alternatives",
        column1="src_tax_id",
        column2="dest_tax_id",
        string="Replaced by",
        readonly=True,
    )
    display_alternative_taxes_field = fields.Boolean(
        compute="_compute_display_alternative_taxes_field"
    )
    is_domestic = fields.Boolean(
        compute="_compute_is_domestic",
        search="_search_is_domestic",
    )
    analytic = fields.Boolean(
        string="Include in Analytic Cost",
        help="If set, the amount computed by this tax will be assigned to the same analytic account as the invoice line (if any)",
    )
    hide_tax_exigibility = fields.Boolean(
        string="Hide Use Cash Basis Option",
        compute="_compute_hide_tax_exigibility",
    )
    tax_exigibility = fields.Selection(
        selection=[
            ("on_invoice", "Based on Invoice"),
            ("on_payment", "Based on Payment"),
        ],
        default="on_invoice",
        help="Based on Invoice: the tax is due as soon as the invoice is validated.\n"
        "Based on Payment: the tax is due as soon as the payment of the invoice is received.",
    )
    cash_basis_transition_account_id = fields.Many2one(
        comodel_name="account.account",
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable'))]",
        check_company=True,
        help="Account used to transition the tax amount for cash basis taxes. It will contain the tax amount as long as the original invoice has not been reconciled ; at reconciliation, this amount cancelled on this account and put on the regular tax account.",
    )
    is_used = fields.Boolean(
        string="Tax used",
        compute="_compute_is_used",
    )
    repartition_lines_str = fields.Char(
        string="Repartition Lines",
        compute="_compute_repartition_lines_str",
        tracking=True,
    )
    invoice_legal_notes = fields.Html(
        string="Legal Notes",
        translate=True,
        help="Legal mentions that have to be printed on the invoices.",
    )

    @api.constrains("tax_exigibility", "cash_basis_transition_account_id")
    def _constrains_cash_basis_transition_account(self):
        for record in self:
            if (
                record.tax_exigibility == "on_payment"
                and not record.cash_basis_transition_account_id.reconcile
                and not self.env.context.get("chart_template_load")
            ):
                raise ValidationError(
                    self.env._(
                        "The cash basis transition account needs to allow reconciliation."
                    )
                )

    @api.model
    @api.readonly
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        domain = Domain(domain or Domain.TRUE)
        if "search_default_domestictax" in self.env.context:
            domain &= Domain("fiscal_position_ids", "=", False) | Domain(
                "fiscal_position_ids.is_domestic", "=", True
            )
        if fp_id := self.env.context.get("dynamic_fiscal_position_id"):
            domain &= Domain("fiscal_position_ids", "in", [False, int(fp_id)])
        if self.env.context.get("hide_original_tax_ids") and fp_id:
            domain &= Domain("replacing_tax_ids", "not any", domain) | Domain.custom(
                to_sql=lambda model, alias, query: SQL(
                    "EXISTS (SELECT 1 FROM %s WHERE %s = %s AND %s = %s)",
                    SQL.identifier("account_tax_alternatives"),
                    SQL.identifier("src_tax_id"),
                    SQL.identifier(alias, "id"),
                    SQL.identifier("dest_tax_id"),
                    SQL.identifier(alias, "id"),
                ),
            )
        _debug.logic(
            "name_search_filtered",
            domestic="search_default_domestictax" in self.env.context,
            fiscal_position=fp_id,
            hide_original=bool(self.env.context.get("hide_original_tax_ids") and fp_id),
        )
        return super().name_search(name, domain, operator, limit)

    def _get_used_tax_ids(self, tax_ids):
        return set()

    @api.depends_context("company")
    def _compute_hide_tax_exigibility(self):
        self.hide_tax_exigibility = self._get_settings_company().account_config_id.tax_exigibility

    @api.depends_context("company")
    @api.depends("fiscal_position_ids")
    def _compute_is_domestic(self):
        domestic = (
            self._get_settings_company().account_config_id.domestic_fiscal_position_id
        )
        for tax in self:
            tax.is_domestic = (
                not tax.fiscal_position_ids or domestic in tax.fiscal_position_ids
            )

    @_debug.perf.timed
    def _search_is_domestic(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        domestic = (
            self._get_settings_company().account_config_id.domestic_fiscal_position_id
        )
        matches = Domain("fiscal_position_ids", "=", False) | Domain(
            "fiscal_position_ids", "in", domestic.ids
        )
        return matches if operator == "in" else ~matches

    @api.depends_context("company")
    @api.depends("fiscal_position_ids", "original_tax_ids")
    def _compute_display_alternative_taxes_field(self):
        for tax in self:
            domestic = tax._get_settings_company().account_config_id.domestic_fiscal_position_id
            tax.display_alternative_taxes_field = tax.original_tax_ids or (
                tax.fiscal_position_ids and tax.fiscal_position_ids._origin != domestic
            )

    @_debug.perf.timed
    def _compute_is_used(self):
        used_taxes = set()

        if self.ids:
            self.env["account.move.line"].flush_model(["tax_ids"])
            used_taxes.update(
                id_
                for [id_] in self.env.execute_query(
                    SQL(
                        """
                        SELECT id
                        FROM account_tax
                        WHERE EXISTS(
                            SELECT 1
                            FROM account_move_line_account_tax_rel AS line
                            WHERE account_tax.id = line.account_tax_id
                        )
                        AND id = ANY(%s)
                        """,
                        list(self.ids),
                    )
                )
            )
            taxes_to_compute = set(self.ids) - used_taxes
            _debug.pipeline(
                "move_line_usage_checked",
                taxes=self,
                used=len(used_taxes),
                remaining=len(taxes_to_compute),
            )

            if taxes_to_compute:
                self.env["account.reconcile.model.line"].flush_model(["tax_ids"])
                used_taxes.update(
                    id_
                    for [id_] in self.env.execute_query(
                        SQL(
                            """
                            SELECT id
                            FROM account_tax
                            WHERE EXISTS(
                                SELECT 1
                                FROM account_reconcile_model_line_account_tax_rel AS reco
                                WHERE account_tax.id = reco.account_tax_id
                            )
                            AND id = ANY(%s)
                            """,
                            list(taxes_to_compute),
                        )
                    )
                )
                taxes_to_compute -= used_taxes

            _debug.pipeline(
                "reco_model_usage_checked",
                used=len(used_taxes),
                remaining=len(taxes_to_compute),
            )
            if taxes_to_compute:
                used_taxes.update(self._get_used_tax_ids(taxes_to_compute))

        _debug.logic(
            "is_used_resolved", taxes=self, has_ids=bool(self.ids), used=len(used_taxes)
        )
        for tax in self:
            tax.is_used = tax._origin.id in used_taxes

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def unlink_except_tax_used(self):
        _debug.lifecycle("unlink_except_tax_used", records=self)
        self.invalidate_recordset(["is_used"])
        if any(self.mapped("is_used")):
            raise ValidationError(
                self.env._(
                    "You cannot delete taxes that are currently in use. Consider archiving them instead."
                )
            )

    @api.model
    @_debug.perf.timed
    def _get_import_criteria_from_invoice_predictive(self, tax_values):
        if "payment_state_before_switch" not in self.env["account.move"]._fields:
            _debug.logic("predictive_skipped", reason="predictive_module_absent")
            return None

        invoice_predictive = tax_values.get("invoice_predictive")
        if not invoice_predictive:
            _debug.logic("predictive_skipped", reason="no_invoice_predictive")
            return None
        _debug.logic(
            "predictive_criterion_built",
            type_tax_use=tax_values.get("type_tax_use"),
            amount_type=tax_values.get("amount_type"),
            amount=tax_values.get("amount"),
        )

        def search_predictive(values):
            domain = values["static_domain"]
            predicted_tax_ids = self.env["account.move.line"]._predict_specific_tax(
                move=invoice_predictive["invoice"],
                name=invoice_predictive["name"],
                partner=invoice_predictive["partner"],
                amount_type=tax_values["amount_type"],
                amount=tax_values["amount"],
                type_tax_use=tax_values["type_tax_use"],
            )
            return (
                self.env["account.tax"]
                .browse(predicted_tax_ids)
                .filtered_domain(domain)[:1]
            )

        return {
            "criteria": [
                {
                    "search_method": search_predictive,
                    "cache_key": frozendict(invoice_predictive),
                }
            ],
        }

    @api.model
    def _get_import_criteria_from_price_include_exclude(self, tax_values):
        price_include = tax_values.get("price_include")
        fiscal_position = tax_values.get("fiscal_position")

        fpos_domain = Domain.TRUE
        if fiscal_position:
            fpos_domain = Domain("fiscal_position_ids", "=", fiscal_position.id)
            if fiscal_position.is_domestic:
                fpos_domain |= Domain("fiscal_position_ids", "=", False)

        criteria = []
        for wanted in (False, True):
            if (wanted and price_include is False) or (not wanted and price_include):
                continue
            include_domain = Domain("price_include", "=", wanted)
            if fiscal_position:
                criteria.append({"domain": include_domain & fpos_domain})
            criteria.append({"domain": include_domain})

        _debug.pipeline(
            "price_include_criteria_built",
            fiscal_position=fiscal_position,
            price_include=price_include,
            criteria=len(criteria),
        )
        return {"criteria": criteria}

    @api.model
    @_debug.perf.timed
    def _update_tax_values_from_search_plan(
        self, search_plan, company, tax_values_list
    ):
        cache = self.env.cr.cache.setdefault("retrieved_tax_map", {}).setdefault(
            company.id, {}
        )

        static_domain = Domain(self._check_company_domain(company))
        for tax_values in tax_values_list:
            tax_domain = (
                Domain("amount_type", "=", tax_values["amount_type"])
                & Domain("type_tax_use", "=", tax_values["type_tax_use"])
                & Domain("amount", "=", tax_values["amount"])
            )
            if "invoice_predictive" in tax_values:
                tax_domain &= Domain(
                    "country_id",
                    "=",
                    tax_values["invoice_predictive"]["invoice"].tax_country_id.id,
                )
            orders = ["sequence", "id"]
            if name := tax_values.get("name"):
                tax_domain &= Domain("name", "=", name)
            if tax_exigibility := tax_values.get("tax_exigibility"):
                tax_domain &= Domain("tax_exigibility", "=", tax_exigibility)
            if (
                ubl_cii_tax_category_code := tax_values.get("ubl_cii_tax_category_code")
            ) and "ubl_cii_tax_category_code" in self._fields:
                tax_domain &= Domain(
                    "ubl_cii_tax_category_code",
                    "in",
                    (ubl_cii_tax_category_code, False),
                )
                orders.insert(0, "ubl_cii_tax_category_code")

            for plan in search_plan:
                tax = None
                plan_values = plan(tax_values)
                if not plan_values:
                    continue

                for criteria in plan_values["criteria"]:
                    domain = criteria.get("domain")
                    search_method = criteria.get("search_method")
                    if domain:
                        domain = tax_domain & Domain(domain)
                        cache_key = repr(domain.optimize(self.env["account.tax"]))
                    else:
                        cache_key = criteria.get("cache_key")
                        if cache_key:
                            cache_key = (cache_key, str(tax_domain))

                    if cache_key and cache_key in cache:
                        if tax := cache[cache_key]:
                            tax_values["tax"] = tax
                            break
                        continue

                    if domain:
                        tax = self._get_first_tax(
                            static_domain & Domain(domain), orders
                        )
                    elif search_method:
                        tax = search_method(
                            {
                                **criteria,
                                "static_domain": tax_domain & static_domain,
                            }
                        )

                    if cache_key:
                        cache[cache_key] = tax
                    if tax:
                        tax_values["tax"] = tax
                        break

                if tax:
                    break
            _debug.logic(
                "import_tax",
                type_tax_use=tax_values.get("type_tax_use"),
                amount=tax_values.get("amount"),
                amount_type=tax_values.get("amount_type"),
                tax=tax_values.get("tax") and tax_values["tax"].id,
            )

    @api.depends(
        "repartition_line_ids.account_id",
        "repartition_line_ids.sequence",
        "repartition_line_ids.factor_percent",
        "repartition_line_ids.use_in_tax_closing",
        "repartition_line_ids.tag_ids",
        "invoice_repartition_line_ids",
        "refund_repartition_line_ids",
    )
    @_debug.perf.timed
    def _compute_repartition_lines_str(self):
        for tax in self:
            repartition_line_info = {}
            invoice_sequence = 0
            refund_sequence = 0
            for repartition_line in tax.repartition_line_ids.sorted(
                key=lambda r: (r.document_type, r.sequence)
            ):
                sequence = (
                    (invoice_sequence := invoice_sequence + 1)
                    if repartition_line.document_type == "invoice"
                    else (refund_sequence := refund_sequence + 1)
                )
                repartition_line_info[(repartition_line.document_type, sequence)] = {
                    "factor_percent": repartition_line.factor_percent,
                    "account": repartition_line.account_id.id or None,
                    "tax_grids": repartition_line.tag_ids.mapped("name") or None,
                    "use_in_tax_closing": bool(repartition_line.use_in_tax_closing),
                }
            tax.repartition_lines_str = str(repartition_line_info)

    def _repartition_line_field_label(self, key):
        return {
            "factor_percent": self.env._("Factor Percent"),
            "account": self.env._("Account"),
            "tax_grids": self.env._("Tax Grids"),
            "use_in_tax_closing": self.env._("Use in tax closing"),
        }.get(key, key)

    def _repartition_line_field_value(self, key, value):
        if value is None:
            return self.env._("None")
        if isinstance(value, bool):
            return self.env._("True") if value else self.env._("False")
        if key == "account" and isinstance(value, int):
            return self.env["account.account"].browse(value).display_name
        return value

    @_debug.perf.timed
    def _prepare_repartition_lines_log_body(self, old_values_str, new_values_str):
        self.check_singleton()
        old_line_values_dict = ast.literal_eval(old_values_str or "{}")
        new_line_values_dict = ast.literal_eval(new_values_str)

        modified_lines = [
            (line, old_line_values_dict[line], new_line_values_dict[line])
            for line in old_line_values_dict.keys() & new_line_values_dict.keys()
        ]
        added_and_deleted_lines = [
            (line, self.env._("Removed"), old_line_values_dict[line])
            if line in old_line_values_dict
            else (line, self.env._("New"), new_line_values_dict[line])
            for line in old_line_values_dict.keys() ^ new_line_values_dict.keys()
        ]
        _debug.logic(
            "repartition_diff_detected",
            tax=self,
            common=len(modified_lines),
            added_or_removed=len(added_and_deleted_lines),
        )

        fragments = []
        for (document_type, sequence), old_value, new_value in modified_lines:
            diff_keys = [
                key
                for key in old_value
                if key in new_value and old_value[key] != new_value[key]
            ]
            if diff_keys:
                body = Markup(
                    "<b>{type}</b> {rep} {seq}:<ul class='mb-0 ps-4'>{changes}</ul>"
                ).format(
                    type=document_type.capitalize(),
                    rep=self.env._("repartition line"),
                    seq=sequence,
                    changes=Markup().join(
                        [
                            Markup("""
                            <li>
                                <span class='o-mail-Message-trackingOld me-1 px-1 text-muted fw-bold'>{old}</span>
                                <i class='o-mail-Message-trackingSeparator fa-solid fa-right-long mx-1 text-600'/>
                                <span class='o-mail-Message-trackingNew me-1 fw-bold text-info'>{new}</span>
                                <span class='o-mail-Message-trackingField ms-1 fst-italic text-muted'>({diff})</span>
                            </li>
                        """).format(
                                old=self._repartition_line_field_value(
                                    diff_key, old_value[diff_key]
                                ),
                                new=self._repartition_line_field_value(
                                    diff_key, new_value[diff_key]
                                ),
                                diff=self._repartition_line_field_label(diff_key),
                            )
                            for diff_key in diff_keys
                        ]
                    ),
                )
                fragments.append(body)

        for (document_type, sequence), operation, value in added_and_deleted_lines:
            body = Markup(
                "<b>{op} {type}</b> {rep} {seq}:<ul class='mb-0 ps-4'>{changes}</ul>"
            ).format(
                op=operation,
                type=document_type.capitalize(),
                rep=self.env._("repartition line"),
                seq=sequence,
                changes=Markup().join(
                    [
                        Markup("""
                        <li>
                            <span class='o-mail-Message-trackingNew me-1 fw-bold text-info'>{value}</span>
                            <span class='o-mail-Message-trackingField ms-1 fst-italic text-muted'>({diff})</span>
                        </li>
                    """).format(
                            value=self._repartition_line_field_value(key, value[key]),
                            diff=self._repartition_line_field_label(key),
                        )
                        for key in value
                    ]
                ),
            )
            fragments.append(body)

        _debug.pipeline("repartition_log_fragments", tax=self, fragments=len(fragments))
        return Markup().join(fragments)

    @_debug.perf.timed
    def _message_log_batch(self, bodies, **kwargs):
        tracking_values = kwargs.get("tracking_values") or {}
        snapshot_field_id = (
            self.env["ir.model.fields"]._get("account.tax", "repartition_lines_str").id
        )

        loggable_ids = []
        kept_per_id = dict(tracking_values)
        repartition_bodies = {}
        for tax in self:
            if not tax.is_used:
                kept_per_id.pop(tax.id, None)
                continue

            kept = []
            fragments = []
            for command in tracking_values.get(tax.id) or []:
                if command[2]["field_id"] == snapshot_field_id:
                    fragments.append(
                        tax._prepare_repartition_lines_log_body(
                            command[2]["old_value_char"],
                            command[2]["new_value_char"],
                        )
                    )
                else:
                    kept.append(command)
            kept_per_id[tax.id] = kept
            if body := Markup().join(fragments):
                repartition_bodies[tax.id] = body

            if kept or bodies.get(tax.id) or tax.id in repartition_bodies:
                loggable_ids.append(tax.id)

        _debug.logic(
            "tax_log_filtered",
            taxes=self,
            loggable=len(loggable_ids),
            repartition_bodies=len(repartition_bodies),
        )
        if not loggable_ids:
            _debug.logic("tax_log_skipped", reason="no_used_tax_with_changes")
            return self.env["mail.message"]
        return super(AccountTax, self.browse(loggable_ids))._message_log_batch(
            {
                id_: self._concat_log_bodies(
                    bodies.get(id_), repartition_bodies.get(id_)
                )
                for id_ in loggable_ids
            },
            **{**kwargs, "tracking_values": kept_per_id},
        )

    @api.model
    def _concat_log_bodies(self, *bodies):
        present = [body for body in bodies if body]
        if not present:
            return ""
        if len(present) == 1:
            return present[0]
        return Markup().join(Markup(body) for body in present)

    def _get_repartition_lines(self, document_type):
        return [
            Command.create(
                {
                    "document_type": document_type,
                    "repartition_type": repartition_type,
                    "tag_ids": [],
                }
            )
            for repartition_type in ("base", "tax")
        ]

    @api.depends("company_ids")
    def _compute_invoice_repartition_line_ids(self):
        for tax in self:
            if not tax.invoice_repartition_line_ids:
                tax.invoice_repartition_line_ids = tax._get_repartition_lines("invoice")

    @api.depends("company_ids")
    def _compute_refund_repartition_line_ids(self):
        for tax in self:
            if not tax.refund_repartition_line_ids:
                tax.refund_repartition_line_ids = tax._get_repartition_lines("refund")

    def _unmerge_action_xmlid(self):
        return "account.action_unmerge_taxes"

    def _unmerge_copy_defaults(self):
        return {}

    def _unmerge_finalize(self, new_record_by_company):
        for new_tax in new_record_by_company.values():
            new_tax.name = self.name

    @_debug.perf.timed
    def _unmerge_split_sidecars(self, new_record_by_company):

        def ordered(tax):
            return tax.repartition_line_ids._sorted_for_positional_pairing()

        source_lines = ordered(self)
        companies = self.env["res.company"].browse(
            company.id for company in new_record_by_company
        )
        descendants = self.env["res.company"].search(
            [("id", "child_of", companies.ids)]
        )
        descendant_ids_by_company = {
            company.id: [
                descendant.id
                for descendant in descendants
                if company in descendant.parent_ids
            ]
            for company in companies
        }
        _debug.pipeline(
            "sidecar_split_started",
            tax=self,
            companies=companies,
            descendants=len(descendants),
            source_lines=len(source_lines),
        )
        self.env["account.move.line"].flush_model(["tax_repartition_line_id"])
        for company, new_tax in new_record_by_company.items():
            mapping = {
                old.id: new.id
                for old, new in zip(source_lines, ordered(new_tax), strict=True)
            }
            _debug.logic(
                "sidecar_mapping_built",
                company=company,
                new_tax=new_tax,
                lines=len(mapping),
                skipped=not mapping,
            )
            if not mapping:
                continue
            self.env.cr.execute(
                SQL(
                    """
                    UPDATE account_move_line
                       SET tax_repartition_line_id =
                           (%(mapping)s::jsonb->>tax_repartition_line_id::text)::int
                     WHERE tax_repartition_line_id IN %(old_ids)s
                       AND company_id IN %(company_ids)s
                    """,
                    mapping=json.dumps({str(k): v for k, v in mapping.items()}),
                    old_ids=tuple(mapping),
                    company_ids=tuple(descendant_ids_by_company[company.id]),
                )
            )
            _debug.perf.count(
                "move_lines_remapped", company=company, rows=self.env.cr.rowcount
            )
        self.env["account.move.line"].invalidate_model(["tax_repartition_line_id"])

    def _get_first_tax(self, domain, orders):
        return self.search(domain, order=",".join(orders), limit=1)

    def _merge_method(self, destination, source):
        raise UserError(self.env._("You cannot merge taxes."))

    @api.constrains("company_ids", "country_id")
    @_debug.perf.timed
    def _check_company_ids_country(self):
        for tax in self:
            if len(tax.company_ids) < 2:
                continue
            for company in tax.company_ids:
                allowed = (
                    company.account_config_id.account_fiscal_country_id
                    | company.account_config_id.multi_vat_foreign_country_ids
                )
                if tax.country_id not in allowed:
                    _debug.logic(
                        "tax_company_country_rejected",
                        tax=tax,
                        company=company,
                        country=tax.country_id,
                    )
                    raise ValidationError(
                        self.env._(
                            "%(company)s does not file taxes for %(country)s, so "
                            "it cannot share the tax %(tax)s.",
                            company=company.display_name,
                            country=tax.country_id.display_name,
                            tax=tax.display_name,
                        )
                    )

    @api.constrains("company_ids")
    @_debug.perf.timed
    def _check_company_consistency(self):
        if self.env.context.get("from_account_tax_creation") is True:
            return
        self.invalidate_recordset(fnames=["company_ids"])
        AccountMoveLine = self.env["account.move.line"]
        line_companies_by_tax = defaultdict(set)
        for tax, company in (
            *AccountMoveLine._read_group(
                [("tax_line_id", "in", self.ids)], ["tax_line_id", "company_id"]
            ),
            *AccountMoveLine._read_group(
                [("tax_ids", "in", self.ids)], ["tax_ids", "company_id"]
            ),
        ):
            line_companies_by_tax[tax.id].add(company)
        for companies, taxes in self.grouped(lambda tax: tax.company_ids).items():
            if any(
                not (companies & line_company.parent_ids)
                for tax in taxes
                for line_company in line_companies_by_tax[tax.id]
            ):
                _debug.logic(
                    "tax_company_change_rejected", taxes=taxes, companies=companies
                )
                raise UserError(
                    self.env._(
                        "You can't change the company of your tax since there are some journal items linked to it."
                    )
                )

    @api.model
    @_debug.perf.timed
    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        base_line = super()._prepare_base_line_for_taxes_computation(record, **kwargs)
        if base_line["account_id"] is False:
            base_line["account_id"] = self._get_base_line_field_value_from_record(
                record, "account_id", kwargs, self.env["account.account"]
            )
        return base_line

    @api.model
    @_debug.perf.timed
    def _prepare_tax_line_for_taxes_computation(self, record, **kwargs):
        def load(field, fallback):
            return self._get_base_line_field_value_from_record(
                record, field, kwargs, fallback
            )

        currency = (
            load("currency_id", None)
            or load("company_currency_id", None)
            or load("company_id", self.env["res.company"]).currency_id
            or self.env["res.currency"]
        )

        return {
            **kwargs,
            "record": record,
            "id": load("id", 0),
            "tax_repartition_line_id": load(
                "tax_repartition_line_id", self.env["account.tax.repartition.line"]
            ),
            "group_tax_id": load("group_tax_id", self.env["account.tax"]),
            "tax_ids": load("tax_ids", self.env["account.tax"]),
            "tax_tag_ids": load("tax_tag_ids", self.env["account.account.tag"]),
            "currency_id": currency,
            "partner_id": load("partner_id", self.env["res.partner"]),
            "account_id": load("account_id", self.env["account.account"]),
            "analytic_distribution": load("analytic_distribution", None),
            "sign": load("sign", 1.0),
            "amount_currency": load("amount_currency", 0.0),
            "balance": load("balance", 0.0),
        }

    @api.model
    @_debug.perf.timed
    def _prepare_base_line_grouping_key(self, base_line):
        return {
            "partner_id": base_line["partner_id"].id,
            "currency_id": base_line["currency_id"].id,
            "analytic_distribution": base_line["analytic_distribution"],
            "account_id": base_line["account_id"].id,
            "tax_ids": [Command.set(base_line["tax_ids"].ids)],
        }

    @_debug.perf.timed
    def _prepare_base_line_tax_repartition_grouping_key(
        self, base_line, base_line_grouping_key, tax_data, tax_rep_data
    ):
        tax = tax_data["tax"]
        tax_rep = tax_rep_data["tax_rep"]
        return {
            **base_line_grouping_key,
            "tax_repartition_line_id": tax_rep.id,
            "partner_id": base_line["partner_id"].id,
            "currency_id": base_line["currency_id"].id,
            "group_tax_id": tax_data["group"].id,
            "analytic_distribution": (
                base_line_grouping_key["analytic_distribution"]
                if tax.analytic or not tax_rep.use_in_tax_closing
                else False
            ),
            "account_id": tax_rep_data["account"].id
            or base_line_grouping_key["account_id"],
            "tax_ids": [Command.set(tax_rep_data["taxes"].ids)],
            "tax_tag_ids": [Command.set(tax_rep_data["tax_tags"].ids)],
            "__keep_zero_line": False,
        }

    @_debug.perf.timed
    def _prepare_tax_line_repartition_grouping_key(self, tax_line):
        return {
            "tax_repartition_line_id": tax_line["tax_repartition_line_id"].id,
            "partner_id": tax_line["partner_id"].id,
            "currency_id": tax_line["currency_id"].id,
            "group_tax_id": tax_line["group_tax_id"].id,
            "analytic_distribution": tax_line["analytic_distribution"],
            "account_id": tax_line["account_id"].id,
            "tax_ids": [Command.set(tax_line["tax_ids"].ids)],
            "tax_tag_ids": [Command.set(tax_line["tax_tag_ids"].ids)],
        }

    def _get_repartition_lines_by_kind(self, is_refund, cache=None):
        self.check_singleton()
        key = (self, is_refund)
        if cache is not None and key in cache:
            return cache[key]

        lines = (
            self.refund_repartition_line_ids
            if is_refund
            else self.invoice_repartition_line_ids
        )
        by_kind = {
            "base": lines.filtered(lambda x: x.repartition_type == "base"),
            "tax": lines.filtered(
                lambda x: x.repartition_type == "tax" and x.factor >= 0.0
            ),
            "reverse_charge": lines.filtered(
                lambda x: x.repartition_type == "tax" and x.factor < 0.0
            ),
        }
        if cache is not None:
            cache[key] = by_kind
        return by_kind

    @_debug.perf.timed
    def _add_accounting_data_to_base_line_tax_details(
        self,
        base_line,
        company,
        include_caba_tags=False,
        repartition_cache=None,
        rounded=True,
    ):
        is_refund = base_line["is_refund"]
        product = base_line["product_id"]

        taxes_data = base_line["tax_details"]["taxes_data"]
        base_line["tax_tag_ids"] = self.env["account.account.tag"]
        product_tags = self.env["account.account.tag"]
        if product:
            product_tags = product.sudo().account_tag_ids
            base_line["tax_tag_ids"] |= product_tags

        for tax_data in taxes_data:
            tax = tax_data["tax"]
            reps_by_kind = tax._get_repartition_lines_by_kind(
                is_refund, repartition_cache
            )

            if not tax_data["is_reverse_charge"] and (
                include_caba_tags or tax.tax_exigibility == "on_invoice"
            ):
                base_line["tax_tag_ids"] |= reps_by_kind["base"].tag_ids

            if tax_data["is_reverse_charge"]:
                tax_reps = reps_by_kind["reverse_charge"]
                tax_rep_sign = -1.0
            else:
                tax_reps = reps_by_kind["tax"]
                tax_rep_sign = 1.0

            self._add_tax_repartition_amounts(
                base_line,
                tax_data,
                tax_reps,
                tax_rep_sign,
                company,
                include_caba_tags=include_caba_tags,
                rounded=rounded,
            )

        self._add_tax_repartition_tags_and_grouping_keys(
            base_line,
            product_tags,
            include_caba_tags=include_caba_tags,
            repartition_cache=repartition_cache,
        )

    @_debug.perf.timed
    def _add_tax_repartition_amounts(
        self,
        base_line,
        tax_data,
        tax_reps,
        tax_rep_sign,
        company,
        include_caba_tags=False,
        rounded=True,
    ):
        currency = base_line["currency_id"]
        company_currency = company.currency_id
        amount_prefix = "" if rounded else "raw_"
        tax_amount_currency = tax_data[f"{amount_prefix}tax_amount_currency"]
        tax_amount = tax_data[f"{amount_prefix}tax_amount"]

        total_tax_rep_amounts = {"tax_amount_currency": 0.0, "tax_amount": 0.0}
        tax_reps_data = tax_data["tax_reps_data"] = []
        for tax_rep in tax_reps:
            tax_rep_data = {
                "tax_rep": tax_rep,
                "tax_amount_currency": currency.round(
                    tax_amount_currency * tax_rep.factor * tax_rep_sign
                ),
                "tax_amount": company_currency.round(
                    tax_amount * tax_rep.factor * tax_rep_sign
                ),
                "account": tax_rep._get_aml_target_tax_account(
                    force_caba_exigibility=include_caba_tags
                )
                or base_line["account_id"],
            }
            total_tax_rep_amounts["tax_amount_currency"] += tax_rep_data[
                "tax_amount_currency"
            ]
            total_tax_rep_amounts["tax_amount"] += tax_rep_data["tax_amount"]
            tax_reps_data.append(tax_rep_data)

        sorted_tax_reps_data = sorted(
            tax_reps_data,
            key=lambda tax_rep: (
                -abs(tax_rep["tax_amount_currency"]),
                -abs(tax_rep["tax_amount"]),
            ),
        )
        for delta_suffix, delta_currency in (
            ("_currency", currency),
            ("", company_currency),
        ):
            field = f"tax_amount{delta_suffix}"
            target_amount = delta_currency.round(tax_data[f"{amount_prefix}{field}"])
            target_factors = [
                {"factor": tax_rep_data[field], "tax_rep_data": tax_rep_data}
                for tax_rep_data in sorted_tax_reps_data
            ]
            amounts_to_distribute = self._distribute_delta_amount_smoothly(
                precision_digits=delta_currency.decimal_places,
                delta_amount=target_amount - total_tax_rep_amounts[field],
                target_factors=target_factors,
            )
            for target_factor, amount_to_distribute in zip(
                target_factors, amounts_to_distribute, strict=True
            ):
                target_factor["tax_rep_data"][field] += amount_to_distribute

    @_debug.perf.timed
    def _add_tax_repartition_tags_and_grouping_keys(
        self, base_line, product_tags, include_caba_tags=False, repartition_cache=None
    ):
        is_refund = base_line["is_refund"]
        subsequent_tags_per_tax = defaultdict(lambda: self.env["account.account.tag"])
        base_line_grouping_key = self._prepare_base_line_grouping_key(base_line)
        for tax_data in reversed(base_line["tax_details"]["taxes_data"]):
            tax = tax_data["tax"]
            keeps_caba_tags = include_caba_tags or tax.tax_exigibility == "on_invoice"

            for tax_rep_data in tax_data["tax_reps_data"]:
                tax_rep = tax_rep_data["tax_rep"]

                tax_rep_data["taxes"] = tax_data["taxes"]
                tax_rep_data["tax_tags"] = product_tags
                if keeps_caba_tags:
                    tax_rep_data["tax_tags"] |= tax_rep.tag_ids
                if tax.include_base_amount:
                    for other_tax, tags in subsequent_tags_per_tax.items():
                        if tax != other_tax:
                            tax_rep_data["tax_tags"] |= tags

                tax_rep_data["grouping_key"] = (
                    self._prepare_base_line_tax_repartition_grouping_key(
                        base_line,
                        base_line_grouping_key,
                        tax_data,
                        tax_rep_data,
                    )
                )

            if tax.is_base_affected and keeps_caba_tags:
                subsequent_tags_per_tax[tax] |= tax._get_repartition_lines_by_kind(
                    is_refund, repartition_cache
                )["base"].tag_ids

    def _add_accounting_data_in_base_lines_tax_details(
        self, base_lines, company, include_caba_tags=False, rounded=True
    ):
        repartition_cache = {}
        for base_line in base_lines:
            self._add_accounting_data_to_base_line_tax_details(
                base_line,
                company,
                include_caba_tags=include_caba_tags,
                repartition_cache=repartition_cache,
                rounded=rounded,
            )

    @api.model
    @_debug.perf.timed
    def _prepare_tax_lines(self, base_lines, company, tax_lines=None):
        tax_lines_mapping, base_lines_to_update = self._aggregate_tax_lines_by_key(
            base_lines
        )
        tax_lines_mapping = self._remove_zero_tax_lines(tax_lines_mapping, company)

        tax_lines_to_update = []
        tax_lines_to_delete = []
        for tax_line in tax_lines or []:
            grouping_key = frozendict(
                self._prepare_tax_line_repartition_grouping_key(tax_line)
            )
            if grouping_key in tax_lines_mapping:
                amounts = tax_lines_mapping.pop(grouping_key)
                tax_lines_to_update.append((tax_line, grouping_key, amounts))
            else:
                tax_lines_to_delete.append(tax_line)
        tax_lines_to_add = [
            {**grouping_key, **values}
            for grouping_key, values in tax_lines_mapping.items()
        ]
        _debug.pipeline(
            "_prepare_tax_lines_line",
            base_lines_count=len(base_lines),
            add=len(tax_lines_to_add),
            update=len(tax_lines_to_update),
            delete=len(tax_lines_to_delete),
            base_update=len(base_lines_to_update),
        )

        return {
            "tax_lines_to_add": tax_lines_to_add,
            "tax_lines_to_delete": tax_lines_to_delete,
            "tax_lines_to_update": tax_lines_to_update,
            "base_lines_to_update": base_lines_to_update,
        }

    @api.model
    @_debug.perf.timed
    def _aggregate_tax_lines_by_key(self, base_lines):
        tax_lines_mapping = defaultdict(
            lambda: {
                "tax_base_amount": 0.0,
                "amount_currency": 0.0,
                "balance": 0.0,
            }
        )

        base_lines_to_update = []
        for base_line in base_lines:
            sign = base_line["sign"]
            tax_details = base_line["tax_details"]
            base_lines_to_update.append(
                (
                    base_line,
                    {
                        "tax_tag_ids": [Command.set(base_line["tax_tag_ids"].ids)],
                        "amount_currency": sign
                        * (
                            tax_details["total_excluded_currency"]
                            + tax_details["delta_total_excluded_currency"]
                        ),
                        "balance": sign
                        * (
                            tax_details["total_excluded"]
                            + tax_details["delta_total_excluded"]
                        ),
                    },
                )
            )
            for tax_data in tax_details["taxes_data"]:
                tax = tax_data["tax"]
                for tax_rep_data in tax_data["tax_reps_data"]:
                    grouping_key = frozendict(tax_rep_data["grouping_key"])
                    tax_line = tax_lines_mapping[grouping_key]
                    tax_line["name"] = base_line.get("manual_tax_line_name", tax.name)
                    tax_line["tax_base_amount"] += sign * tax_data["base_amount"]
                    tax_line["amount_currency"] += (
                        sign * tax_rep_data["tax_amount_currency"]
                    )
                    tax_line["balance"] += sign * tax_rep_data["tax_amount"]
        _debug.pipeline(
            "tax_lines_aggregated",
            base_lines=len(base_lines),
            grouping_keys=len(tax_lines_mapping),
        )
        return tax_lines_mapping, base_lines_to_update

    @api.model
    def _remove_zero_tax_lines(self, tax_lines_mapping, company):
        return {
            frozendict(
                {
                    grouping_k: k[grouping_k]
                    for grouping_k in k
                    if not grouping_k.startswith("__")
                }
            ): v
            for k, v in tax_lines_mapping.items()
            if (
                k["__keep_zero_line"]
                or (
                    not self.env["res.currency"]
                    .browse(k["currency_id"])
                    .is_zero(v["amount_currency"])
                    or not company.currency_id.is_zero(v["balance"])
                )
            )
        }

    def _get_repartition_tags(self, is_refund, repartition_type):
        document_type = "refund" if is_refund else "invoice"
        return self.repartition_line_ids.filtered(
            lambda x: (
                x.repartition_type == repartition_type
                and x.document_type == document_type
            )
        ).mapped("tag_ids")

    @_debug.perf.timed
    def _get_all_tax_values(self, tax_details, currency, partner, round_base):
        taxes = []
        void_amount = 0.0
        for tax_data in tax_details["taxes_data"]:
            tax = tax_data["tax"]
            for tax_rep_data in tax_data["tax_reps_data"]:
                rep_line = tax_rep_data["tax_rep"]
                taxes.append(
                    {
                        "id": tax.id,
                        "name": (partner and tax.with_context(lang=partner.lang).name)
                        or tax.name,
                        "amount": tax_rep_data["tax_amount_currency"],
                        "base": (
                            currency.round(tax_data["raw_base_amount_currency"])
                            if round_base
                            else tax_data["raw_base_amount_currency"]
                        ),
                        "sequence": tax.sequence,
                        "account_id": tax_rep_data["account"].id,
                        "analytic": tax.analytic,
                        "use_in_tax_closing": rep_line.use_in_tax_closing,
                        "is_reverse_charge": tax_data["is_reverse_charge"],
                        "price_include": tax.price_include,
                        "tax_exigibility": tax.tax_exigibility,
                        "tax_repartition_line_id": rep_line.id,
                        "group": tax_data["group"],
                        "tag_ids": tax_rep_data["tax_tags"].ids,
                        "tax_ids": tax_rep_data["taxes"].ids,
                    }
                )
                if not rep_line.account_id:
                    void_amount += tax_rep_data["tax_amount_currency"]
        return taxes, void_amount

    @_debug.perf.timed
    def compute_all(
        self,
        price_unit,
        currency=None,
        quantity=1.0,
        product=None,
        partner=None,
        is_refund=False,
        handle_price_include=True,
        rounding_method=None,
        *,
        include_caba_tags=False,
    ):
        company = self._get_settings_company()
        company = company._get_accessible_branches()[:1] or company

        currency = currency or company.currency_id
        special_mode = self._get_all_special_mode(handle_price_include)
        base_line = self._prepare_base_line_for_taxes_computation(
            None,
            partner_id=partner,
            currency_id=currency,
            product_id=product,
            tax_ids=self,
            price_unit=price_unit,
            quantity=quantity,
            is_refund=is_refund,
            special_mode=special_mode,
        )
        self._add_tax_details_in_base_line(
            base_line, company, rounding_method=rounding_method
        )
        self._add_accounting_data_to_base_line_tax_details(
            base_line, company, include_caba_tags=include_caba_tags, rounded=False
        )

        tax_details = base_line["tax_details"]
        total_void = total_excluded = tax_details["raw_total_excluded_currency"]
        total_included = tax_details["raw_total_included_currency"]
        round_base = self.env.context.get("round_base", True)

        taxes, void_amount = self._get_all_tax_values(
            tax_details, currency, partner, round_base
        )
        total_void += void_amount
        _debug.logic(
            "compute_all",
            compute_all=self,
            price=price_unit,
            qty=quantity,
            special=special_mode,
            excl=total_excluded,
            incl=total_included,
            taxes=len(taxes),
        )

        if round_base:
            total_excluded = currency.round(total_excluded)
            total_included = currency.round(total_included)

        return {
            "base_tags": base_line["tax_tag_ids"].ids,
            "taxes": taxes,
            "total_excluded": total_excluded,
            "total_included": total_included,
            "total_void": total_void,
        }


class AccountTaxRepartitionLine(models.Model):
    _inherit = "account.tax.repartition.line"

    account_id = fields.Many2one(
        comodel_name="account.account",
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'off_balance'))]",
        check_company=True,
        help="Account on which to post the tax amount",
    )
    tag_ids = fields.Many2many(
        comodel_name="account.account.tag",
        string="Tax Grids",
        copy=True,
        domain=[("applicability", "=", "taxes")],
        ondelete="restrict",
    )
    use_in_tax_closing = fields.Boolean(
        string="Tax Closing Entry",
        compute="_compute_use_in_tax_closing",
        precompute=True,
        store=True,
        readonly=False,
    )
    tag_ids_domain = fields.Binary(
        string="tag domain",
        compute="_compute_tag_ids_domain",
        help="Dynamic domain used for the tag that can be set on tax",
    )

    def _sorted_for_positional_pairing(self):
        return self.sorted(
            lambda line: (
                line.document_type,
                line.repartition_type,
                line.sequence,
                line.factor_percent,
                line.account_id.id or 0,
            )
        )

    @api.depends_context("company")
    def _compute_tag_ids_domain(self):
        for rep_line in self:
            company = rep_line.tax_id._get_settings_company()
            allowed_country_ids = (
                False,
                company.account_config_id.account_fiscal_country_id.id,
                *company.account_config_id.multi_vat_foreign_country_ids.ids,
            )
            rep_line.tag_ids_domain = [
                ("applicability", "=", "taxes"),
                ("country_id", "in", allowed_country_ids),
            ]

    @api.depends("account_id", "repartition_type")
    def _compute_use_in_tax_closing(self):
        for rep_line in self:
            rep_line.use_in_tax_closing = (
                rep_line.repartition_type == "tax"
                and rep_line.account_id
                and rep_line.account_id.internal_group not in ("income", "expense")
            )

    @api.onchange("repartition_type")
    def _onchange_repartition_type(self):
        if self.repartition_type == "base":
            self.account_id = None

    def _get_aml_target_tax_account(self, force_caba_exigibility=False):
        self.check_singleton()
        if (
            not force_caba_exigibility
            and self.tax_id.tax_exigibility == "on_payment"
            and not self.env.context.get("caba_no_transition_account")
        ):
            return self.tax_id.cash_basis_transition_account_id
        else:
            return self.account_id
