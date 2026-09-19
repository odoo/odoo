import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..tools import SETTLED_STATES, Verdict

_logger = logging.getLogger(__name__)

_OPEN_STATES = ("draft", "queued", "sent")


class ExchangeTransmission(models.Model):
    _name = "exchange.transmission"
    _description = "Exchange Transmission"
    _order = "date_created desc, id desc"
    _rec_name = "display_name"

    # FIELDS

    # Subject block
    subject_id = fields.Reference(
        selection="_selection_subject_models",
        index=True,
        required=True,
        help="The business record this transmission is about.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        required=True,
    )

    # Channel block
    channel_id = fields.Many2one(
        comodel_name="exchange.channel",
        index=True,
        required=True,
        ondelete="restrict",
    )
    protocol = fields.Selection(
        related="channel_id.protocol",
    )

    # Lifecycle block
    intent = fields.Selection(
        selection=[
            ("issue", "Issue"),
            ("annul", "Annul"),
            ("amend", "Amend"),
            ("query", "Query"),
        ],
        default="issue",
        index=True,
        required=True,
        help="What we are asking the counterparty for. Separate from state "
        "because an annulment that failed is intent=annul, state=rejected -- "
        "not a value in the issuing field.",
    )
    document_kind = fields.Selection(
        selection="_selection_document_kind",
        index=True,
        help="Which document this is, when a counterparty takes more than one "
        "about the same record -- an invoice and its expense classification, a "
        "CFDI and the payment complement. Not a phase and not an ask: the third "
        "axis l10n_mx_edi flattened into its sixteen-value state.",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("queued", "Queued"),
            ("sent", "Sent"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("expired", "Expired"),
        ],
        default="draft",
        index=True,
        required=True,
        help="Where the ask has got to, as the counterparty sees it. Whether "
        "the call itself completed is on the event log, not here.",
    )
    is_settled = fields.Boolean(
        compute="_compute_is_settled",
        store=True,
        index=True,
    )

    # Timing block
    date_created = fields.Datetime(
        default=fields.Datetime.now,
        index=True,
        readonly=True,
        required=True,
    )
    date_sent = fields.Datetime(readonly=True)
    date_settled = fields.Datetime(readonly=True)

    # Payload block
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        ondelete="set null",
        help="What we sent, exactly as it went.",
    )
    response_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        ondelete="set null",
        help="What came back, exactly as it arrived.",
    )
    reference = fields.Char(
        index=True,
        help="The counterparty's own identifier for this exchange, whatever "
        "it calls it -- uuid, mark, index, zip key, CSV.",
    )
    message = fields.Text(
        readonly=True,
        help="The counterparty's own words. Never paraphrased.",
    )

    # Relation block
    parent_id = fields.Many2one(
        comodel_name="exchange.transmission",
        index=True,
        ondelete="cascade",
        help="The transmission this one acts upon: an annulment's issue, an "
        "amendment's original.",
    )
    chain_previous_id = fields.Many2one(
        comodel_name="exchange.transmission",
        index=True,
        ondelete="restrict",
        help="The previous link, for a counterparty that requires each "
        "document to reference the one before it.",
    )

    # Retry block
    retry_count = fields.Integer(
        default=0,
        readonly=True,
    )
    date_next_retry = fields.Datetime(
        index=True,
        readonly=True,
    )

    # Transport block
    event_log_id = fields.Many2one(
        comodel_name="integration.exchange",
        index=True,
        ondelete="set null",
        help="The transport record: whether the call completed. A settled "
        "transmission whose call failed is a contradiction, and the "
        "constraint below says so.",
    )

    display_name = fields.Char(compute="_compute_display_name")

    # INDEXES

    _queue_idx = models.Index("(state, date_next_retry)")
    _subject_idx = models.Index("(subject_id, intent)")
    _reference_uniq = models.UniqueIndex(
        "(channel_id, reference, intent, document_kind) WHERE reference IS NOT NULL",
        "A counterparty issues one reference per ask.",
    )

    # CONSTRAINT METHODS

    @api.constrains("state", "event_log_id")
    def _check_state_agrees_with_transport(self):
        for transmission in self:
            log = transmission.event_log_id
            if not log:
                continue
            if transmission.state == "accepted" and log.state == "failed":
                raise ValidationError(
                    self.env._(
                        "Transmission %(name)s is accepted while the call that "
                        "carried it failed. One of the two readings is wrong.",
                        name=transmission.display_name,
                    ),
                )

    @api.constrains("parent_id")
    def _check_parent_id(self):
        for transmission in self:
            if transmission.parent_id and transmission.intent == "issue":
                raise ValidationError(
                    self.env._("An issuing transmission acts upon nothing."),
                )

    @api.constrains("document_kind", "channel_id")
    def _check_document_kind_belongs_to_the_protocol(self):
        for transmission in self:
            kind = transmission.document_kind
            if not kind:
                continue
            protocol, _, _rest = kind.partition(".")
            if protocol != transmission.protocol:
                raise ValidationError(
                    self.env._(
                        "%(kind)s is a document of the %(owner)s protocol, and "
                        "this transmission goes over %(protocol)s.",
                        kind=kind,
                        owner=protocol,
                        protocol=transmission.protocol,
                    ),
                )

    @api.constrains("chain_previous_id")
    def _check_chain_previous_id(self):
        for transmission in self:
            previous = transmission.chain_previous_id
            if previous and previous.channel_id != transmission.channel_id:
                raise ValidationError(
                    self.env._("A chain does not cross channels."),
                )

    # COMPUTE METHODS

    @api.depends("state")
    def _compute_is_settled(self):
        for transmission in self:
            transmission.is_settled = transmission.state in SETTLED_STATES

    @api.depends("intent", "state", "channel_id.name", "reference")
    def _compute_display_name(self):
        intents = dict(self._fields["intent"]._description_selection(self.env))
        states = dict(self._fields["state"]._description_selection(self.env))
        for transmission in self:
            label = f"{intents.get(transmission.intent, '')} / {states.get(transmission.state, '')}"
            if transmission.reference:
                label = f"{transmission.reference} - {label}"
            transmission.display_name = label

    # CRUD METHODS

    @api.model_create_multi
    def create(self, vals_list):
        transmissions = super().create(vals_list)
        transmissions._notify_subjects()
        transmissions.filtered(
            lambda transmission: transmission.state == "queued"
        ).channel_id._enqueue_send()
        return transmissions

    def write(self, vals):
        result = super().write(vals)
        if {"state", "intent"} & set(vals):
            self._notify_subjects()
        return result

    # HELPER METHODS

    def _notify_subjects(self) -> None:
        for subject in {transmission.subject_id for transmission in self}:
            subject._on_transmission_changed()

    @api.model
    def _selection_document_kind(self) -> list[tuple[str, str]]:
        return self.env["exchange.protocol"]._selection_document_kind()

    @api.model
    def _selection_subject_models(self) -> list[tuple[str, str]]:
        mixin_cls = self.env.registry.get("mixin.exchange.subject")
        if not mixin_cls:
            return []

        subjects = []
        pending = list(mixin_cls._inherit_children)
        seen = set()
        while pending:
            name = pending.pop(0)
            if name in seen or name == "mixin.exchange.subject":
                continue
            seen.add(name)

            model_cls = self.env.registry.get(name)
            if not model_cls:
                continue
            pending.extend(model_cls._inherit_children)
            if not getattr(model_cls, "_abstract", False):
                subjects.append(
                    (name, getattr(model_cls, "_description", None) or name)
                )
        return sorted(subjects, key=lambda subject: subject[1])

    def _get_protocol(self):
        self.check_singleton()
        return self.channel_id._get_protocol()

    # ACTION METHODS

    def action_send(self) -> None:
        self._send_many()

    def action_read_verdict(self) -> None:
        for transmission in self:
            transmission._read_verdict()

    def action_view_subject(self) -> dict:
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.subject_id._name,
            "res_id": self.subject_id.id,
            "view_mode": "form",
        }

    # EXCHANGE METHODS

    def _send(self) -> None:
        self.check_singleton()
        self._send_many()

    def _claim(self):
        claimed = self.try_lock_for_update()
        if len(claimed) < len(self):
            _logger.info(
                "Left %s transmission(s) to the sender already holding them",
                len(self) - len(claimed),
            )
        return claimed

    def _send_many(self) -> None:
        ready = self.browse()
        for transmission in self._claim():
            if transmission.is_settled:
                raise UserError(
                    self.env._(
                        "Transmission %(name)s is settled and cannot be sent again.",
                        name=transmission.display_name,
                    ),
                )
            errors = transmission._get_protocol()._get_message_errors(transmission)
            if errors:
                transmission._settle(
                    Verdict(state="rejected", message="\n".join(errors)),
                )
            else:
                ready |= transmission

        grouped = ready.grouped(
            lambda transmission: (transmission.channel_id, transmission.document_kind)
        )
        for (channel, _kind), group in grouped.items():
            protocol = channel._get_protocol()
            size = max(getattr(protocol, "_batch_size", 1) or 1, 1)
            for start in range(0, len(group), size):
                group[start : start + size]._send_chunk(protocol)

    def _send_chunk(self, protocol) -> None:
        try:
            verdicts = protocol._send_batch(self)
        except Exception as error:
            _logger.exception(
                "Sending %s transmission(s) over %s failed",
                len(self),
                self.channel_id.display_name,
            )
            for transmission in self:
                transmission._schedule_retry(str(error))
            return

        now = fields.Datetime.now()
        for transmission in self:
            verdict = verdicts.get(transmission.id)
            if verdict is None:
                # The counterparty took the batch and said nothing about this
                # member. Leaving it queued is the safe reading: the next run
                # asks again, where dropping it would lose the document.
                _logger.error(
                    "%s returned no verdict for transmission %s in a batch of %s",
                    protocol._name,
                    transmission.id,
                    len(self),
                )
                continue
            transmission.date_sent = now
            transmission._apply(verdict)

    def _read_verdict(self) -> None:
        self.check_singleton()
        if self.state != "sent":
            return
        verdict = self._get_protocol()._read_verdict(self)
        if verdict is not None:
            self._apply(verdict)

    def _apply(self, verdict: Verdict) -> None:
        self.check_singleton()
        if verdict.is_settled:
            self._settle(verdict)
            return

        values = {
            "state": verdict.state,
            "date_next_retry": self._get_next_retry(verdict.retry_after),
            **verdict.values,
        }
        if verdict.reference:
            values["reference"] = verdict.reference
        if verdict.message:
            values["message"] = verdict.message
        self.write(values)
        self._add_response(verdict)

    def _settle(self, verdict: Verdict) -> None:
        self.check_singleton()
        values = {
            "state": verdict.state,
            "date_settled": fields.Datetime.now(),
            "date_next_retry": False,
            **verdict.values,
        }
        if verdict.reference:
            values["reference"] = verdict.reference
        if verdict.message:
            values["message"] = verdict.message
        self.write(values)
        self._add_response(verdict)
        self.subject_id._on_transmission_settled(self)

    def _schedule_retry(self, message: str) -> None:
        self.check_singleton()
        channel = self.channel_id
        attempt = self.retry_count + 1
        if not channel.is_retry_required(attempt):
            self._settle(
                Verdict(
                    state="rejected",
                    message=self.env._(
                        "Gave up after %(attempts)s attempts. Last error: %(message)s",
                        attempts=attempt,
                        message=message,
                    ),
                ),
            )
            return
        delay = channel.get_retry_delay(attempt)
        self.write(
            {
                "state": "queued",
                "retry_count": attempt,
                "message": message,
                "date_next_retry": fields.Datetime.now() + timedelta(seconds=delay),
            },
        )
        # The endpoint's own backoff, carried as the job's `eta`. `ir_job` owns
        # when the work runs; `retry_count` stays here because how many times a
        # counterparty has been asked is an audit trail, not scheduling state.
        channel._enqueue_send(delay=delay)

    def _get_next_retry(self, retry_after: int | None):
        if retry_after is None:
            return False
        return fields.Datetime.now() + timedelta(seconds=retry_after)

    def _add_attachment(self, document) -> None:
        self.check_singleton()
        if self.attachment_id:
            return
        self.attachment_id = self.env["ir.attachment"].create(
            {
                "name": document.name or f"{self.id}.bin",
                "raw": document.data,
                "mimetype": document.mimetype,
                "res_model": self._name,
                "res_id": self.id,
            },
        )

    def _add_response(self, verdict: Verdict) -> None:
        self.check_singleton()
        if not verdict.response:
            return
        self.response_attachment_id = self.env["ir.attachment"].create(
            {
                "name": verdict.response_name or f"{self.id}-response.bin",
                "raw": verdict.response,
                "res_model": self._name,
                "res_id": self.id,
            },
        )

    # CRON METHODS

    @api.model
    def _cron_send_queued(self, limit: int = 100) -> None:
        """Sweep for queued work no job is carrying.

        Sending is a worker's job now -- `create` and `_schedule_retry` enqueue
        one per channel. This is the safety net for a transmission that reached
        `queued` by some other road: a data import, a restored backup, or a job
        lost to a crash between enqueue and run. Enqueuing is idempotent, so
        sweeping something already carried costs nothing.
        """
        now = fields.Datetime.now()
        self.search(
            [
                ("state", "=", "queued"),
                "|",
                ("date_next_retry", "=", False),
                ("date_next_retry", "<=", now),
            ],
            limit=limit,
        ).channel_id._enqueue_send()

    @api.model
    def _cron_read_verdicts(self, limit: int = 100) -> None:
        pending = self.search([("state", "=", "sent")], limit=limit)
        for transmission in pending:
            try:
                with self.env.cr.savepoint():
                    transmission._read_verdict()
            except Exception:
                _logger.exception(
                    "Reading the verdict of transmission %s failed", transmission.id
                )
