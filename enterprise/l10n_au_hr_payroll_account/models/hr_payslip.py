# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_list, groupby


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    has_superstream = fields.Boolean(compute="_compute_has_superstream")
    l10n_au_stp_status = fields.Selection([
        ("draft", "Draft"),
        ("ready", "Ready"),
        ("sent", "Submitted"),
        ("error", "Error"),
    ], string="STP Status", compute="_compute_stp_status")
    l10n_au_stp_count = fields.Integer(compute='_compute_stp_count')
    l10n_au_finalised = fields.Boolean("Finalised", default=False, readonly=True, copy=False)
    net_wage = fields.Monetary(tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        payslips = super().create(vals_list)
        au_payslips = payslips.filtered(lambda p: p.country_code == 'AU')
        if au_payslips:
            au_payslips._add_to_stp()
        return payslips

    @api.depends("state", "employee_id")
    def _compute_stp_count(self):
        slip_stp = self._get_payslip_stp()
        for slip in self:
            slip.l10n_au_stp_count = len(slip_stp[slip.id])

    @api.depends('state')
    def _compute_has_superstream(self):
        for rec in self:
            rec.has_superstream = bool(rec._get_superstreams())

    @api.depends('state')
    def _compute_stp_status(self):
        stp_records = self.env['l10n_au.stp'].search([
            '|',
                ('payslip_ids', 'in', self.ids),
                ('l10n_au_stp_emp.employee_id', 'in', self.employee_id.ids)
        ], order="id desc")
        for payslip in self:
            if payslip.country_code != 'AU':
                payslip.l10n_au_stp_status = False
            elif payslip.state not in ('done', 'paid'):
                payslip.l10n_au_stp_status = 'draft'
            else:
                # Use latest STP record for the payslip for ffr
                stp = stp_records.filtered(lambda r: payslip in r.payslip_ids or payslip.employee_id in r.l10n_au_stp_emp.employee_id)[:1]
                payslip.l10n_au_stp_status = 'sent' if stp.state == 'sent' else 'ready'

    def _compute_payslip_ytd_totals(self):
        super()._compute_payslip_ytd_totals()
        au_slips = self.filtered(lambda x: x.country_code == "AU")
        if not au_slips:
            return
        # Add opening balances to the YTD totals
        PayslipYTD = self.env["l10n_au.payslip.ytd"]
        opening_balances = PayslipYTD.search_fetch(
            [("employee_id", "in", au_slips.employee_id.ids)],
            ["employee_id", "rule_id", "ytd_amount", "start_date"]
        )
        ote_by_date = {}
        for start_date, slips in self.grouped(lambda x: PayslipYTD._get_start_date(x.date_from)).items():
            ote_by_date[start_date] = self.env['l10n_au.payslip.ytd']._get_ote_total(slips.employee_id.ids, start_date)

        for payslip in au_slips:
            totals = self._clean_payslip_ytd_totals(payslip.payslip_ytd_totals)
            fiscal_start_date = PayslipYTD._get_start_date(payslip.date_from)
            employee_opening_balances = opening_balances.filtered(
                lambda x: x.employee_id == payslip.employee_id and x.start_date == fiscal_start_date
            )

            # Add opening balances to the earliest income stream type for that fiscal year
            slips = payslip._l10n_au_get_year_to_date_slips()
            if slips:
                income_stream_type = slips and slips[0].l10n_au_income_stream_type
            else:
                income_stream_type = payslip.employee_id.l10n_au_income_stream_type

            slip_lines = totals[income_stream_type]["slip_lines"]
            for balance in employee_opening_balances:
                slip_lines[balance.rule_id.category_id.code]["total"] += balance.ytd_amount
                slip_lines[balance.rule_id.category_id.code][balance.rule_id.code] += balance.ytd_amount
                # Gross is calculated using the the formula used for salary rules
                if balance.rule_id.category_id.code in ["BASIC", "ALW", "SALARY.SACRIFICE", "WORK.GIVING", "RTW", "EXTRA"]:
                    if balance.code == "ALW.TAXFREE":
                        amount = 0
                    elif balance.rule_id.code == "SUPER.CONTRIBUTION":
                        amount = -balance.l10n_au_payslip_ytd_input_ids.filtered(lambda x: x.input_type.code == "SS.S").ytd_amount
                    else:
                        amount = balance.ytd_amount
                    slip_lines["GROSS"]["GROSS"] += amount
                    slip_lines["GROSS"]["total"] += amount

            # Rules with custom computation method
            # OTE is calculated from individual input types and work entry types on opening balances
            slip_lines["OTE"]["OTE"] += ote_by_date[fiscal_start_date][payslip.employee_id.id]
            slip_lines["OTE"]["total"] += ote_by_date[fiscal_start_date][payslip.employee_id.id]

            child_support_garnishee = sum(employee_opening_balances.l10n_au_payslip_ytd_input_ids.filtered(
                lambda l: l.res_model == "hr.payslip.input.type" and l.input_type.code == "CHILD_SUPPORT_GARNISHEE").mapped("ytd_amount"))
            slip_lines["CHILD.SUPPORT.GARNISHEE"]["CHILD.SUPPORT.GARNISHEE"] += child_support_garnishee
            slip_lines["CHILD.SUPPORT.GARNISHEE"]["total"] += child_support_garnishee

            sacrifice_total = slip_lines["SALARY.SACRIFICE"]["SALARY.SACRIFICE.OTHER"] - sum(
                employee_opening_balances.l10n_au_payslip_ytd_input_ids.filtered(lambda x:  x.input_type.code == "SS.S").mapped("ytd_amount"))
            slip_lines["SALARY.SACRIFICE.TOTAL"]["SALARY.SACRIFICE.TOTAL"] += sacrifice_total
            slip_lines["SALARY.SACRIFICE.TOTAL"]["total"] += sacrifice_total

            # Update the worked days totals for leaves etc.
            for work_entry_line in employee_opening_balances.l10n_au_payslip_ytd_input_ids.filtered(lambda l: l.res_model == "hr.work.entry.type" and l.ytd_amount):
                totals[income_stream_type]["worked_days"][work_entry_line.work_entry_type.id]["amount"] += work_entry_line.ytd_amount
                totals[income_stream_type]["worked_days"][work_entry_line.work_entry_type.id]["payroll_code"] = work_entry_line.work_entry_type.l10n_au_work_stp_code
                totals[income_stream_type]["worked_days"][work_entry_line.work_entry_type.id]["is_leave"] = work_entry_line.work_entry_type.is_leave

            # Add the opening balances for input lines to the YTD totals
            for input_line in employee_opening_balances.l10n_au_payslip_ytd_input_ids.filtered(lambda l: l.res_model == "hr.payslip.input.type" and l.ytd_amount):
                if input_line.res_id not in totals[income_stream_type]["input_lines"]:
                    totals[income_stream_type]["input_lines"][input_line.res_id] = {
                        "amount": 0.0,
                        "code": input_line.input_type.code,
                        "payroll_code": input_line.input_type.l10n_au_payroll_code,
                        "payment_type": input_line.input_type.l10n_au_payment_type,
                        "payroll_code_description": input_line.input_type.l10n_au_payroll_code_description,
                    }
                totals[income_stream_type]["input_lines"][input_line.res_id]["amount"] += input_line.ytd_amount
            payslip.payslip_ytd_totals = totals

    def action_payslip_done(self):
        """
            Generate the superstream record for all australian payslips with
            superannuation salary rules.
        """
        super().action_payslip_done()
        self.filtered(lambda p: p.country_code == 'AU')._add_payslip_to_superstream()
        # If the payslip is part of a FFR STP, find a payment to reconcile
        clearing_house = self.env.ref('l10n_au_hr_payroll_account.res_partner_clearing_house', raise_if_not_found=False)
        if not clearing_house:
            raise UserError(_("No clearing house record found for this company!"))
        super_account = clearing_house.property_account_payable_id
        failed_reconciliation = []
        for payslip in self:
            if payslip.country_code != 'AU' or payslip.move_id.state == 'posted':
                continue
            stp_reports = self.env['l10n_au.stp'].search([('payslip_ids', '=', payslip.id), ('ffr', '=', True)])
            if not stp_reports.filtered(lambda r: payslip in r.payslip_ids):
                continue
            # Auto post and reconcile the existing payment
            payslip.move_id._post(soft=False)
            if payslip.payslip_run_id:
                payments = payslip.payslip_run_id.l10n_au_payment_batch_id\
                    .payment_ids.filtered(lambda p: p.partner_id == payslip.employee_id.work_contact_id and not p.is_reconciled)
            else:
                payments = self.env["account.payment"].search(
                    [
                        ("partner_id", "=", payslip.employee_id.work_contact_id.id),
                        ("is_reconciled", "=", False),
                        ("payment_type", "=", "outbound"),
                        ("date", "=", payslip.paid_date),
                    ]
                )
            if len(payments) == 1:

                valid_accounts = self.env['account.payment']\
                    .with_context(hr_payroll_payment_register=True)\
                    ._get_valid_payment_account_types()
                lines_to_reconcile = payslip.move_id.line_ids.filtered(
                    lambda line: line.account_id != super_account
                    and line.account_id.account_type in valid_accounts
                    and not line.currency_id.is_zero(line.amount_residual_currency)
                )
                payment_lines = payments.move_id.line_ids.filtered_domain([
                    ('parent_state', '=', 'posted'),
                    ('account_type', 'in', valid_accounts),
                    ('reconciled', '=', False),
                ])
                (lines_to_reconcile + payment_lines).reconcile()
            else:
                failed_reconciliation.append(payslip.name)
        if failed_reconciliation:
            return {'warning': {
                'title': _("Warning"),
                'message': _(
                    "Failed to reconcile the following payslips with their payments: %s", format_list(self.env, failed_reconciliation))
            }}

    def _clear_super_stream_lines(self):
        to_delete = self.env["l10n_au.super.stream.line"].search([('payslip_id', 'in', self.ids)])
        to_delete.unlink()

    def action_payslip_cancel(self):
        self._clear_super_stream_lines()
        return super().action_payslip_cancel()

    def action_payslip_draft(self):
        self._clear_super_stream_lines()
        au_slips = self.filtered(lambda p: p.country_code == 'AU')
        if not self.env.context.get("allow_ffr") and any(state == 'sent' for state in au_slips.mapped("l10n_au_stp_status")):
            raise UserError(_("A payslip cannot be reset to draft after submitting to ATO."))
        return super().action_payslip_draft()

    def _get_superstreams(self):
        return self.env["l10n_au.super.stream.line"].search([("payslip_id", "in", self.ids)]).l10n_au_super_stream_id

    def _add_payslip_to_superstream(self):
        if not self:
            return

        if not self.company_id.l10n_au_hr_super_responsible_id:
            raise UserError(_("This company does not have an employee responsible for managing SuperStream. "
                              "You can set one in Payroll > Configuration > Settings."))

        # Get latest draft superstream, if any, else create new
        superstream = self.env['l10n_au.super.stream'].search([('state', '=', 'draft')], order='create_date desc', limit=1)
        if not superstream:
            superstream = self.env['l10n_au.super.stream'].create({})

        super_line_vals = []
        for payslip in self:
            if not payslip.line_ids.filtered(lambda line: line.code == "SUPER"):
                continue
            super_accounts = payslip.employee_id._get_active_super_accounts()

            if not super_accounts:
                raise UserError(_(
                    "No active super account found for the employee %s. "
                    "Please create a super account before proceeding",
                    payslip.employee_id.name))

            super_line_vals += [{
                "l10n_au_super_stream_id": superstream.id,
                "employee_id": payslip.employee_id.id,
                "payslip_id": payslip.id,
                "sender_id": payslip.company_id.l10n_au_hr_super_responsible_id.id,
                "super_account_id": account.id,
            } for account in super_accounts]

        return self.env["l10n_au.super.stream.line"].create(super_line_vals)

    def action_open_superstream(self):
        return self._get_superstreams()._get_records_action()

    def _is_past_period(self, get_employees=False):
        """ Check if there is an existing STP record for the employee in the future.
            returns: Bool if get_employees is False else list of employees.
        """
        # if the payslip period is before an already submitted submit event.
        stp = self.env["l10n_au.stp"].search(
            [
                # Necessary to only filter on stp created before the payslip, else it will return True in the future.
                ("create_date", "<", self[-1].create_date),
                ("state", "=", "sent"),
                ("payevent_type", "=", "submit"),
                ("submit_date", ">=", self[-1].date_from),
                ("payslip_ids.employee_id", "in", self.employee_id.ids),
                ("company_id", "=", self.company_id.id),
            ],
            order="create_date desc",
            limit=1,
        )
        return stp.payslip_ids.employee_id if get_employees else bool(stp)

    def _get_payslip_stp(self):
        stp_ids = self.env['l10n_au.stp'].search([
            ('payslip_ids', 'in', self.ids),
            ('state', '!=', 'cancel'),
        ])
        slip_stps = defaultdict(lambda x: self.env['l10n_au.stp'])
        for slip in self:
            # For submit events
            if submit_stp := stp_ids.filtered_domain([
                ("payevent_type", "=", "submit"),
                ('payslip_ids', '=', slip.id),
            ]):
                slip_stps[slip.id] = submit_stp
            else:
                # For update events
                slip_stps[slip.id] = stp_ids.filtered_domain([
                        ('payevent_type', '=', 'update'),
                        ('l10n_au_stp_emp.employee_id', '=', slip.employee_id.id),
                        ('is_finalisation', '=', False),
                        ('is_unfinalisation', '=', False),
                        ('is_zeroing', '=', False),
                ])
        return slip_stps

    def _add_to_stp(self):
        """
            Generate STP entry for the payslip.
            For current and future pay period, a Submit event STP entry will be created.
            For past pay period, an Update event STP entry will be created.
        """
        payevnt_type = "submit"
        if employees_to_update := self._is_past_period(get_employees=True):
            payevnt_type = "update"
        stp = self.env["l10n_au.stp"].search(
            [
                ("state", "=", "draft"),
                ("payevent_type", "=", payevnt_type),
                ("payslip_batch_id", "=", self.payslip_run_id.id),
                ('company_id', '=', self.company_id.id)
            ],
            order="create_date desc",
            limit=1,
        )

        if not stp:
            stp = self.env['l10n_au.stp'].create({'company_id': self.company_id.id, 'payevent_type': payevnt_type})

        if payevnt_type == "submit":
            stp.write({
                'payslip_batch_id': self.payslip_run_id.id,
                'payslip_ids': [Command.link(rec) for rec in self.ids],
            })
        else:
            if self.employee_id != employees_to_update:
                raise UserError(_("There are existing STP records for the following employee(s) at a later date. "
                                  "Please remove them from this batch, create a separate batch with these employees "
                                  "and proceed with another submission (update event).\n%s", "\n".join(employees_to_update.mapped('name'))))
            stp.write({"l10n_au_stp_emp": [(0, 0, {"employee_id": e.id}) for e in self.employee_id]})

    def action_open_payslip_stp(self):
        self.ensure_one()
        return self._get_payslip_stp()[self.id]._get_records_action(name=_("Single Touch Payroll"))

    def action_register_payment(self):
        """ Exclude the super payment lines from the payment.
            Super lines will be registered with the superstream record.
        """
        res = super().action_register_payment()
        clearing_house = self.env.ref('l10n_au_hr_payroll_account.res_partner_clearing_house', raise_if_not_found=False)
        if not clearing_house:
            raise UserError(_("No clearing house record found for this company!"))
        super_account = clearing_house.property_account_payable_id
        lines_to_exclude = self.move_id.line_ids.filtered(lambda l: l.account_id == super_account)
        res['context']['active_ids'] = [l for l in res['context']['active_ids'] if l not in lines_to_exclude.ids]
        return res

    def action_payslip_payment_report(self, export_format='aba'):
        action = super().action_payslip_payment_report()
        if self.company_id.country_code != 'AU':
            return action
        action.update({
            'context': {
                **action['context'],
                'default_export_format': export_format,
            },
        })
        return action

    def _l10n_au_get_year_to_date_totals(self, fields_to_compute=None, l10n_au_include_current_slip=False, include_ytd_balances=True, zero_amount=False, employee_id=None, start_date=None):
        fields_to_compute = fields_to_compute or []
        # Change to a parameter in master
        group_income_stream_types = self.env.context.get("group_income_stream_types", False)
        if zero_amount:
            zeroed_totals = {
                "slip_lines": {
                    "WITHHOLD.TOTAL": {"WITHHOLD.TOTAL": 0.0},
                    "OTE": {"OTE": 0.0},
                    "SUPER": {"SUPER": 0.0},
                },
                "worked_days": {},
                "periods": 0,
                "fields": {"l10n_au_extra_compulsory_super": 0.0},
            }
            if group_income_stream_types:
                return {income_stream_type: zeroed_totals for income_stream_type in set(self._l10n_au_get_year_to_date_slips().mapped("l10n_au_income_stream_type"))}
            return zeroed_totals

        employee_id = self.env["hr.employee"].browse(employee_id) if employee_id else self.employee_id
        start_date = self.date_from if self else start_date

        if self:
            totals = super()._l10n_au_get_year_to_date_totals(fields_to_compute=fields_to_compute, l10n_au_include_current_slip=l10n_au_include_current_slip)
        else:
            # Allow to compute YTD totals for an employee without a payslip.
            #  A dummy slip is initialized in such a case.
            if not employee_id:
                raise UserError(_("Payslip or Employee is required to compute YTD totals."))

            with self.env.cr.savepoint(flush=False) as sp:
                dummy_slip = self.new({"employee_id": employee_id, "date_from": start_date})
                totals = dummy_slip._l10n_au_get_year_to_date_totals()
                sp.rollback()
        return totals

    def _l10n_au_get_ytd_inputs(self, l10n_au_include_current_slip=False, include_ytd_balances=True, zero_amount=False, employee_id=None, start_date=None):
        """ Return the year to date amounts for inputs for the payslip.
            include_ytd_balances: Include the YTD Opening balances for the payslip.
            zero_amount: Return the all inputs with 0 amount for zeroing STP.
        """
        # Change to a parameter in master
        group_income_stream_types = self.env.context.get("group_income_stream_types", False)
        if zero_amount:
            if group_income_stream_types:
                return {income_stream_type: {} for income_stream_type in set(self._l10n_au_get_year_to_date_slips().mapped("l10n_au_income_stream_type"))}
            return {}

        employee_id = self.env["hr.employee"].browse(employee_id) if employee_id else self.employee_id
        start_date = self.date_from if self else start_date

        if self:
            totals = super()._l10n_au_get_ytd_inputs(l10n_au_include_current_slip=l10n_au_include_current_slip)
        else:
            # Allow to compute YTD totals for an employee without a payslip.
            # A dummy slip is initialized in such a case.
            if not employee_id:
                raise UserError(_("Payslip or Employee is required to compute YTD totals."))

            with self.env.cr.savepoint(flush=False) as sp:
                dummy_slip = self.new({"employee_id": employee_id, "date_from": start_date})
                totals = dummy_slip._l10n_au_get_ytd_inputs()
                sp.rollback()

        return totals

    def _get_payslip_lines(self):
        lines = super()._get_payslip_lines()
        au_slips = self.filtered(lambda x: x.country_code == "AU")
        if not au_slips:
            return lines
        rules = self.env["hr.salary.rule"].search_read([("struct_id.country_id", "=", self.env.ref("base.au").id)], ["code", "category_id"], load="")
        rules = {rule["id"]: rule for rule in rules}
        categories = self.env["hr.salary.rule.category"].search_read([], ["code"])
        categories = {category["id"]: category["code"] for category in categories}
        for slip_id, slip_lines in groupby(lines, lambda x: x["slip_id"]):
            if slip_id not in au_slips.ids:
                continue
            ytd_total = self.browse(slip_id)._l10n_au_get_year_to_date_totals(l10n_au_include_current_slip=False)
            for line in slip_lines:
                rule = rules.get(line["salary_rule_id"])
                line["ytd"] = ytd_total["slip_lines"][categories[rule['category_id']]][rule["code"]] + line["total"]
        return lines

    def _compute_worked_days_ytd(self):
        super()._compute_worked_days_ytd()
        au_slips = self.filtered(lambda x: x.country_code == "AU")
        if not au_slips:
            return
        # Recompute the YTD since Australian payroll supports missed reporting.
        # So all the new slips after missed report will need a new sum
        # Also includes opening balances. No recalculation as it is already cached.
        for slip in au_slips:
            ytd_totals = slip._l10n_au_get_year_to_date_totals()
            for worked_day in slip.worked_days_line_ids:
                worked_day.ytd = ytd_totals["worked_days"][worked_day.work_entry_type_id.id]["amount"] + worked_day.amount
