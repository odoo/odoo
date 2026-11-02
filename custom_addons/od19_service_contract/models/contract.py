# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ContractContract(models.Model):
    """Thin wrapper over OCA ``contract.contract`` for recurring services.

    The OCA engine owns recurrence, the auto-invoicing cron, the portal,
    mail and templates. This module only adds what a *service* contract
    needs: the "service" flag, the link to preventive-maintenance cards and
    covered warranty lots, plus renewal (manual and automatic) and an
    expiry notice.
    """

    _inherit = "contract.contract"

    is_service_contract = fields.Boolean(
        string="Service Contract",
        tracking=True,
        help="Tick to manage this contract as a recurring service contract "
        "(PM / AMC). Service contracts appear under Accounting > Customers > "
        "Service Contracts.",
    )
    service_card_ids = fields.One2many(
        comodel_name="od19.service.card",
        inverse_name="contract_id",
        string="Service Cards",
        help="Preventive-maintenance cards delivered under this contract.",
    )
    service_card_count = fields.Integer(
        compute="_compute_service_card_count",
    )
    warranty_lot_ids = fields.Many2many(
        comodel_name="stock.lot",
        relation="od19_service_contract_warranty_lot_rel",
        column1="contract_id",
        column2="lot_id",
        string="Covered Warranty Lots",
        help="Lots / serials whose warranty is covered by this contract.",
    )
    auto_renew = fields.Boolean(
        string="Auto Renew",
        tracking=True,
        help="Automatically extend the contract when it reaches its end date.",
    )
    renewal_interval_months = fields.Integer(
        string="Renewal Interval (Months)",
        default=12,
        help="How many months the contract is extended by each renewal.",
    )
    renewal_notice_days = fields.Integer(
        string="Renewal Notice (Days)",
        default=30,
        help="Raise a reminder this many days before the end date.",
    )
    renewal_notice_sent = fields.Boolean(
        string="Renewal Notice Sent",
        copy=False,
        help="Internal flag preventing duplicate renewal reminders.",
    )
    is_expiring_soon = fields.Boolean(
        string="Expiring Soon",
        compute="_compute_is_expiring_soon",
    )

    @api.depends("service_card_ids")
    def _compute_service_card_count(self):
        for contract in self:
            contract.service_card_count = len(contract.service_card_ids)

    @api.depends("active", "date_end", "renewal_notice_days")
    def _compute_is_expiring_soon(self):
        today = fields.Date.context_today(self)
        for contract in self:
            contract.is_expiring_soon = bool(
                contract.active
                and contract.date_end
                and today <= contract.date_end
                and (contract.date_end - today).days <= contract.renewal_notice_days
            )

    def action_renew(self):
        """Extend every dated contract line by ``renewal_interval_months``.

        The contract-level ``date_end`` is computed from the lines, so
        extending the lines renews the contract. The OCA engine resumes
        billing on its own: once ``date_end`` moves past the line's
        ``last_date_invoiced`` the line becomes invoiceable again.
        """
        for contract in self:
            lines = contract.contract_line_ids.filtered("date_end")
            if not lines:
                raise UserError(
                    _("Cannot renew a contract without dated contract lines.")
                )
            months = contract.renewal_interval_months or 12
            for line in lines:
                line.date_end = line.date_end + relativedelta(months=months)
            contract.renewal_notice_sent = False
        return True

    @api.model
    def cron_service_contract_renewal(self):
        """Daily job: auto-renew expired contracts and warn about upcoming ones."""
        today = fields.Date.context_today(self)
        contracts = self.search(
            [
                ("is_service_contract", "=", True),
                ("active", "=", True),
                ("date_end", "!=", False),
            ]
        )
        for contract in contracts:
            if contract.auto_renew and contract.date_end < today:
                contract.action_renew()
                continue
            if contract.renewal_notice_sent:
                continue
            days_left = (contract.date_end - today).days
            if 0 <= days_left <= contract.renewal_notice_days:
                contract.activity_schedule(
                    "mail.mail_activity_data_todo",
                    date_deadline=contract.date_end,
                    summary=_("Service contract %s expires soon") % contract.name,
                    note=_(
                        "Contract %(name)s will expire on %(date)s "
                        "(%(days)s day(s) left). Please review the renewal."
                    )
                    % {
                        "name": contract.name,
                        "date": contract.date_end,
                        "days": days_left,
                    },
                    user_id=contract.user_id.id or self.env.uid,
                )
                contract.renewal_notice_sent = True
        return True

    def action_view_service_cards(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Service Cards"),
            "res_model": "od19.service.card",
            "view_mode": "list,form",
            "domain": [("contract_id", "=", self.id)],
            "context": {
                "default_contract_id": self.id,
                "default_partner_id": self.partner_id.id,
            },
        }
