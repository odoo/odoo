from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

from odoo.addons.mail.tools.discuss import Store

_debug = DebugLog(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

    rating_ids = fields.One2many(
        comodel_name="rating.rating",
        inverse_name="message_id",
        string="Related ratings",
    )
    # Stored: the message store reads it on every thread load, and a stored
    # column travels with the message row where a one2many scan is a query
    # per batch.
    rating_id = fields.Many2one(
        comodel_name="rating.rating",
        compute="_compute_rating_id",
        store=True,
    )
    rating_value = fields.Float(
        compute="_compute_rating_value",
        search="_search_rating_value",
        compute_sudo=True,
        store=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        # A message is created before any rating names it: saying so spares
        # the compute a one2many read per batch on every message created.
        for vals in vals_list:
            vals.setdefault("rating_id", False)
        messages = super().create(vals_list)
        _debug.lifecycle("create", messages=messages)
        return messages

    @api.depends("rating_ids.consumed")
    @_debug.perf.timed
    def _compute_rating_id(self):
        for message in self:
            message.rating_id = message.rating_ids.filtered(
                lambda rating: rating.consumed
            ).sorted("create_date", reverse=True)[:1]

    @api.depends("rating_id.rating")
    def _compute_rating_value(self):
        for message in self:
            message.rating_value = (
                message.rating_id.rating if message.rating_id else 0.0
            )

    def _search_rating_value(self, operator, operand):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        ratings = (
            self.env["rating.rating"]
            .sudo()
            ._search(
                [
                    ("rating", operator, operand),
                    ("message_id", "!=", False),
                    ("consumed", "=", True),
                ]
            )
        )
        domain = Domain("id", "in", ratings.subselect("message_id"))
        if operator == "in" and 0 in operand:
            return domain | Domain("rating_ids", "=", False)
        return domain

    def _to_store_defaults(self, target):
        # sudo: mail.message - guest and portal user can receive rating of accessible message
        return super()._to_store_defaults(target) + [
            Store.One("rating_id", sudo=True),
            "record_rating",
        ]

    def _to_store(self, store: Store, fields, **kwargs):
        super()._to_store(store, [f for f in fields if f != "record_rating"], **kwargs)
        if "record_rating" in fields:
            for records in self._records_by_model_name().values():
                if issubclass(
                    self.pool[records._name], self.pool["mixin.rating"]
                ) and records._has_field_access(records._fields["rating_avg"], "read"):
                    all_stats = {}
                    if records._allow_publish_rating_stats():
                        all_stats = records._rating_get_stats_per_record()
                    record_fields = [
                        "rating_avg",
                        "rating_count",
                        Store.Attr(
                            "rating_stats",
                            lambda record, all_stats=all_stats: all_stats.get(
                                record.id
                            ),
                            predicate=lambda record: (
                                record._allow_publish_rating_stats()
                            ),
                        ),
                    ]
                    store.add(records, record_fields, as_thread=True)

    def _is_empty(self):
        return super()._is_empty() and not self.rating_id
