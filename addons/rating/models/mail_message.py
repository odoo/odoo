# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = 'mail.message'

    rating_ids = fields.One2many("rating.rating", "message_id", string="Related ratings")
    rating_id = fields.Many2one("rating.rating", compute="_compute_rating_id")
    rating_value = fields.Float(
        'Rating Value', compute='_compute_rating_value', compute_sudo=True,
        store=False, search='_search_rating_value')

    @api.depends("rating_ids.consumed")
    def _compute_rating_id(self):
        for message in self:
            message.rating_id = message.rating_ids.filtered(lambda rating: rating.consumed).sorted(
                "create_date", reverse=True
            )[:1]

    @api.depends('rating_ids', 'rating_ids.rating')
    def _compute_rating_value(self):
        for message in self:
            message.rating_value = message.rating_id.rating if message.rating_id else 0.0

    def _search_rating_value(self, operator, operand):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        ratings = self.env['rating.rating'].sudo()._search([
            ('rating', operator, operand),
            ('message_id', '!=', False),
            ('consumed', '=', True),
        ])
        domain = Domain("id", "in", ratings.subselect("message_id"))
        if operator == "in" and 0 in operand:
            return domain | Domain("rating_ids", "=", False)
        return domain

    def _store_message_fields(self, res: Store.FieldList, **kwargs):
        super()._store_message_fields(res, **kwargs)
        # sudo: mail.message - guest and portal user can receive rating of accessible message
        res.one("rating_id", "_store_rating_fields", sudo=True)
        records_by_model = self._records_by_model_name()
        r_stats = {}

        def is_rating_mixin(model_name):
            return issubclass(self.pool[model_name], self.pool["rating.mixin"])

        valid_models = set()
        for model_name, records in records_by_model.items():
            if not is_rating_mixin(model_name):
                continue
            valid_models.add(model_name)
            if records.has_access("read") and records._allow_publish_rating_stats():
                # sudo: rating.rating - reading rating stats on readable records is allowed
                r_stats.update(records.sudo()._rating_get_stats_per_record())
        res.many(
            "records",
            lambda res: (
                res.attr(
                    "rating_avg",
                    predicate=lambda r: r.has_field_access(r._fields["rating_avg"], "read"),
                ),
                res.attr(
                    "rating_count",
                    predicate=lambda r: r.has_field_access(r._fields["rating_count"], "read"),
                ),
                res.attr("rating_stats", lambda r: r_stats[r], predicate=lambda r: r in r_stats),
            ),
            as_thread=True,
            only_data=True,
            value=lambda m: records_by_model.get(m.model),
            predicate=lambda m: m.model in valid_models,
        )

    def _is_empty(self):
        return super()._is_empty() and not self.rating_id
