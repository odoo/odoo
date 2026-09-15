from odoo import _, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class AccountFollowupCustomHandler(models.AbstractModel):
    _name = "account.followup.report.handler"
    _inherit = "account.partner.ledger.report.handler"
    _description = "Follow-Up Report Custom Handler"

    @_debug.perf.timed
    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        options["buttons"].append(
            {
                "name": _("Send"),
                "action": "action_send_follow_up",
                "sequence": 100,
                "always_show": True,
            }
        )

        options["custom_display_config"]["components"]["AccountReportLine"] = (
            "PartnerLedgerFollowupLine"
        )
        options["custom_display_config"]["templates"]["AccountReportHeader"] = (
            "account.PartnerLedgerFollowupHeader"
        )

        if self.env.ref(
            "account.pdf_export_main_customer_report", raise_if_not_found=False
        ):
            options["custom_display_config"].setdefault("pdf_export", {})[
                "pdf_export_main"
            ] = "account.pdf_export_main_customer_report"

        options["hide_initial_balance"] = True
        if len(options["partner_ids"]) == 1:
            options["ignore_totals_below_sections"] = True
            options["hide_partner_totals"] = True

        if (
            options["report_id"] != previous_options.get("report_id")
            and options["export_mode"] != "print"
        ):
            options["unreconciled"] = True

        if options["export_mode"] == "print":
            # When printing the report, we don't want to include `no_followup` lines.
            options["forced_domain"] = options.get("forced_domain", []) + [
                ("no_followup", "=", False)
            ]
        _debug.logic(
            "followup_options_resolved",
            report=report,
            partners=len(options["partner_ids"]),
            hide_partner_totals=options.get("hide_partner_totals", False),
            unreconciled=options.get("unreconciled"),
            export_mode=options["export_mode"],
            report_switched=options["report_id"] != previous_options.get("report_id"),
        )

    def _filter_overdue_amls_from_results(self, aml_results):
        return list(
            filter(
                lambda aml: (
                    aml["date_maturity"] and aml["date_maturity"] < fields.Date.today()
                ),
                aml_results,
            )
        )

    def _filter_due_amls_from_results(self, aml_results):
        return list(
            filter(
                lambda aml: (
                    not aml["date_maturity"]
                    or aml["date_maturity"] >= fields.Date.today()
                ),
                aml_results,
            )
        )

    @_debug.perf.timed
    def _get_partner_aml_report_lines(
        self,
        report,
        options,
        partner_line_id,
        aml_results,
        progress,
        offset=0,
        level_shift=0,
    ):

        def create_status_line(status_name):
            return {
                "id": report._get_generic_line_id(
                    None, None, markup=status_name, parent_line_id=partner_line_id
                ),
                "name": status_name,
                "level": 3 + level_shift,
                "parent_id": partner_line_id,
                "columns": [{} for _col in options["columns"]],
                "unfolded": True,
            }

        def get_aml_lines_with_status_line(
            status_name, status_line_id, aml_values, treated_results_count, progress
        ):
            lines = []
            next_progress = progress
            has_more = False

            if not status_line_id or offset == 0:
                status_line = create_status_line(status_name)
                lines.append(status_line)
                status_line_id = status_line["id"]

            for aml_value in aml_values:
                if self._is_report_limit_reached(
                    report, options, treated_results_count
                ):
                    # We loaded one more than the limit on purpose: this way we know we need a "load more" line
                    has_more = True
                    break

                aml_report_line = self._get_report_line_move_line(
                    options,
                    aml_value,
                    status_line_id,
                    next_progress,
                    level_shift=level_shift + 1,
                )
                lines.append(aml_report_line)
                next_progress = self._init_load_more_progress(options, aml_report_line)
                treated_results_count += 1

            return lines, next_progress, treated_results_count, has_more

        lines = []
        next_progress = progress
        has_more = False
        treated_results_count = 0
        due_line_id, overdue_line_id = self._get_unfolded_partner_status_lines(
            report, options, partner_line_id
        )

        overdue_aml_values = self._filter_overdue_amls_from_results(aml_results)
        due_aml_values = self._filter_due_amls_from_results(aml_results)
        _debug.pipeline(
            "followup_amls_split",
            report=report,
            partner_line=partner_line_id,
            aml_results=len(aml_results),
            overdue=len(overdue_aml_values),
            due=len(due_aml_values),
            offset=offset,
            overdue_line_unfolded=bool(overdue_line_id),
            due_line_unfolded=bool(due_line_id),
        )

        if overdue_aml_values:
            overdue_lines, next_progress, treated_results_count, has_more = (
                get_aml_lines_with_status_line(
                    _("Overdue"),
                    overdue_line_id,
                    overdue_aml_values,
                    treated_results_count,
                    next_progress,
                )
            )
            lines.extend(overdue_lines)
            if (
                self._is_report_limit_reached(report, options, treated_results_count)
                and due_aml_values
            ):
                has_more = True

        if due_aml_values and not has_more:
            due_lines, next_progress, treated_results_count, has_more = (
                get_aml_lines_with_status_line(
                    _("Due"),
                    due_line_id,
                    due_aml_values,
                    treated_results_count,
                    next_progress,
                )
            )
            lines.extend(due_lines)

        _debug.pipeline(
            "followup_lines_built",
            report=report,
            partner_line=partner_line_id,
            lines=len(lines),
            treated=treated_results_count,
            has_more=has_more,
        )
        return lines, next_progress, treated_results_count, has_more

    def _get_unfolded_partner_status_lines(self, report, options, partner_line_id):
        _dummy1, _dummy2, partner_id = report._parse_line_id(partner_line_id)[-1]
        due_line_id, overdue_line_id = None, None
        for line_id in options["unfolded_lines"]:
            res_ids_map = report._get_res_ids_from_line_id(
                line_id, ["account.report", "res.partner"]
            )
            if (
                "res.partner" in res_ids_map
                and res_ids_map["account.report"] == report.id
                and res_ids_map["res.partner"] == partner_id
            ):
                markup, _dummy1, _dummy2 = report._parse_line_id(line_id)[-1]
                if markup == "Due":
                    due_line_id = line_id
                if markup == "Overdue":
                    overdue_line_id = line_id
        return due_line_id, overdue_line_id

    def _prepare_aml_order_by_sql(self):
        return SQL(
            "account_move_line.date_maturity, %(order_by)s",
            order_by=super()._prepare_aml_order_by_sql(),
        )

    @_debug.perf.timed
    def action_send_follow_up(self, options):
        _debug.lifecycle("action_send_follow_up", records=self)
        template = self.env.ref(
            "account.email_template_customer_follow_up_report", False
        )
        partners = self.env["res.partner"].browse(options.get("partner_ids", []))
        return {
            "name": _("Send %s Follow Up Report", partners.name)
            if len(partners) == 1
            else _("Send Follow Up Reports"),
            "type": "ir.actions.act_window",
            "views": [[False, "form"]],
            "res_model": "account.report.send",
            "target": "new",
            "context": {
                "default_mail_template_id": template.id,
                "default_report_options": options,
            },
        }
