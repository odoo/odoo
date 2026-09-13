from collections import defaultdict

from odoo import api, fields, models


class PartnerScoreLine(models.Model):
    _name = "partner.score.line"
    _description = "Partner Score Line"
    _order = "partner_id, dimension, id"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        index=True,
        required=True,
        ondelete="cascade",
    )
    dimension = fields.Selection(
        selection=[
            ("partner_attr", "Contact Attribute"),
        ],
        required=True,
        help="Scoring dimension this row belongs to.",
    )
    source_key = fields.Char(
        index=True,
        required=True,
        help="Stable identity of the row's source, as record ids -- e.g. "
        "'crop:12' or 'partner_attr:5:19'. This is what the refresh matches on, "
        "so a row survives a rename, a translation and a rescore from a session "
        "in another language.",
    )
    source_ref = fields.Char(
        compute="_compute_source_ref",
        help="Human-readable source of the points, resolved from source_key in "
        "the reader's language: the crop, bucket or attribute value that "
        "produced them.",
    )
    points = fields.Float(help="Points contributed by this source.")
    max_points = fields.Float(
        help="Ceiling of the dimension/attribute group this row belongs to "
        "(context for the reader). The normalization denominator comes from "
        "the catalog -- see res.partner._get_score_max_possible."
    )
    applied = fields.Boolean(
        default=True,
        help="Unchecked when the aggregation mode discarded this "
        "contribution (e.g. not the highest value under 'max').",
    )
    note = fields.Char(compute="_compute_note")

    @api.depends("dimension", "source_key")
    @api.depends_context("lang")
    def _compute_source_ref(self):
        partner_model = self.env["res.partner"]
        keys_by_dimension = defaultdict(set)
        for row in self:
            keys_by_dimension[row.dimension].add(row.source_key)
        labels = {}
        for dimension, keys in keys_by_dimension.items():
            labels[dimension] = getattr(partner_model, f"_score_labels_{dimension}")(
                keys
            )
        for row in self:
            row.source_ref = labels[row.dimension].get(row.source_key, row.source_key)

    @api.depends("dimension", "source_key", "applied")
    @api.depends_context("lang")
    def _compute_note(self):
        partner_model = self.env["res.partner"]
        for row in self:
            row.note = partner_model._score_row_note(
                row.dimension, row.source_key, row.applied
            )

    _SCORE_ROW_KEY = ("partner_id", "dimension", "source_key")
    _SCORE_ROW_VALUES = ("points", "max_points", "applied")

    @api.model
    def _reconcile_rows(self, partners, rows):
        score_model = self.env(su=True)[self._name]
        existing = score_model.search([("partner_id", "in", partners.ids)])

        by_key = {}
        for row in existing:
            key = (row.partner_id.id, row.dimension, row.source_key)
            by_key.setdefault(key, []).append(row)

        to_create = []
        # Ids, not a recordset union: |= reallocates the whole id tuple on every
        # row, which is quadratic in the number of audit rows in the batch.
        matched_ids = set()
        for vals in rows:
            key = tuple(vals[name] for name in self._SCORE_ROW_KEY)
            candidates = by_key.get(key)
            if not candidates:
                to_create.append(vals)
                continue
            row = candidates.pop(0)
            matched_ids.add(row.id)
            changed = {
                name: vals[name]
                for name in self._SCORE_ROW_VALUES
                if row[name] != vals[name]
            }
            if changed:
                row.write(changed)

        stale = existing.filtered(lambda row: row.id not in matched_ids)
        if stale:
            stale.unlink()
        if to_create:
            score_model.create(to_create)
