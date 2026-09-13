from odoo import fields, models
from odoo.exceptions import UserError

from .exchange_transmission import _OPEN_STATES


class MixinExchangeSubject(models.AbstractModel):
    _name = "mixin.exchange.subject"
    _description = "Exchange Subject Mixin"

    transmission_ids = fields.One2many(
        comodel_name="exchange.transmission",
        compute="_compute_transmissions",
    )
    count_transmission = fields.Integer(compute="_compute_transmissions")
    exchange_state = fields.Selection(
        selection=[
            ("none", "Nothing sent"),
            ("pending", "In flight"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("annulled", "Annulled"),
        ],
        string="Exchange Status",
        compute="_compute_exchange_state",
        help="Rolled up from this record's transmissions. The counterparty's "
        "verdict, not whether a call completed.",
    )

    def _compute_transmissions(self):
        by_reference: dict[str, list[int]] = {}
        if self.ids:
            groups = self.env["exchange.transmission"]._read_group(
                domain=self._get_domain_transmission(),
                groupby=["subject_id"],
                aggregates=["id:recordset"],
            )
            for reference, recordset in groups:
                by_reference[reference] = recordset.ids
        for record in self:
            found = by_reference.get(f"{record._name},{record.id}", [])
            record.transmission_ids = [(6, 0, found)]
            record.count_transmission = len(found)

    def _compute_exchange_state(self):
        for record in self:
            record.exchange_state = record._get_exchange_state()

    def action_view_transmissions(self) -> dict:
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Transmissions"),
            "res_model": "exchange.transmission",
            "view_mode": "list,form",
            "domain": [("subject_id", "=", f"{self._name},{self.id}")],
        }

    def _get_exchange_channel(self):
        raise NotImplementedError(
            f"{self._name} inherits mixin.exchange.subject without saying "
            "which channel its records reach",
        )

    def _get_exchange_channel_of(self, protocol: str):
        self.check_singleton()
        company = self.company_id or self.env.company
        channels = self.env["exchange.channel"]
        for domain in (
            [("protocol", "=", protocol), ("company_id", "=", company.id)],
            [("protocol", "=", protocol), ("company_id", "=", False)],
        ):
            if found := channels.search(domain, limit=1):
                return found
        return channels

    def _get_domain_transmission(self) -> list:
        return [
            (
                "subject_id",
                "in",
                [f"{record._name},{record.id}" for record in self],
            ),
        ]

    def _get_exchange_state(self) -> str:
        self.check_singleton()
        transmissions = self.transmission_ids
        if not transmissions:
            return "none"

        annulled = transmissions.filtered(
            lambda transmission: (
                transmission.intent == "annul" and transmission.state == "accepted"
            )
        )
        if annulled:
            return "annulled"

        issued = transmissions.filtered(
            lambda transmission: transmission.intent in ("issue", "amend")
        )
        if any(transmission.state in _OPEN_STATES for transmission in issued):
            return "pending"
        if any(transmission.state == "accepted" for transmission in issued):
            return "accepted"
        if any(transmission.state == "rejected" for transmission in issued):
            return "rejected"
        return "none"

    def _prepare_transmission_vals(
        self, intent: str, channel=None, kind: str = ""
    ) -> dict:
        self.check_singleton()
        channel = channel or self._get_exchange_channel()
        if not channel:
            raise UserError(
                self.env._(
                    "No exchange channel is configured for %(record)s.",
                    record=self.display_name,
                ),
            )
        values = {
            "subject_id": f"{self._name},{self.id}",
            "channel_id": channel.id,
            "intent": intent,
            "state": "queued",
            "company_id": (self.company_id or self.env.company).id,
        }
        if kind:
            values["document_kind"] = self.env["exchange.protocol"]._get_document_kind(
                channel.protocol, kind
            )
        if intent in ("annul", "amend"):
            values["parent_id"] = self._get_settled_transmission("issue", kind=kind).id
        if channel.is_chained:
            values["chain_previous_id"] = channel.transmission_ids.filtered(
                lambda transmission: transmission.state == "accepted"
            )[:1].id
        return values

    def _add_transmission(self, intent: str = "issue", channel=None, kind: str = ""):
        self.check_singleton()
        return self.env["exchange.transmission"].create(
            self._prepare_transmission_vals(intent, channel=channel, kind=kind),
        )

    def _get_settled_transmission(self, intent: str, kind: str = ""):
        self.check_singleton()
        return self.transmission_ids.filtered(
            lambda transmission: (
                transmission.intent == intent
                and transmission.state == "accepted"
                and (not kind or transmission.document_kind.endswith(f".{kind}"))
            )
        )[:1]

    def _on_transmission_changed(self) -> None:
        self.invalidate_recordset(
            ["transmission_ids", "count_transmission", "exchange_state"],
        )

    def _on_transmission_settled(self, transmission) -> None:
        return
