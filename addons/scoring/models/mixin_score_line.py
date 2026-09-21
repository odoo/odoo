from collections import defaultdict

from odoo import api, fields, models


class MixinScoreLine(models.AbstractModel):
    """One audit row of a subject's score.

    The concrete model declares ``subject_id``, a Many2one to its host with
    ``ondelete="cascade"``, so foreign keys, cascades and record rules stay
    where a polymorphic reference would lose them.
    """

    _name = "mixin.score.line"
    _description = "Score Line Mixin"

    dimension_id = fields.Many2one(
        comodel_name="scorecard.dimension",
        index=True,
        required=True,
        ondelete="cascade",
    )
    dimension_code = fields.Selection(related="dimension_id.code")
    source_key = fields.Char(
        index=True,
        required=True,
        help="Stable identity of the row's source, as record ids -- e.g. "
        "'crop:12' or 'partner_attr:5:19'. This is what the refresh matches on, "
        "so a row survives a rename, a translation and a rescore from a session "
        "in another language.",
    )
    grouping_key = fields.Char(
        required=True,
        help="The group whose ceiling max_points is: one attribute of a catalog "
        "dimension, or the measured dimension itself. The denominator counts "
        "each group once, however many rows it has.",
    )
    source_ref = fields.Char(
        compute="_compute_source_ref",
        help="Human-readable source of the points, resolved from source_key in "
        "the reader's language: the crop, bucket, band or attribute value that "
        "produced them.",
    )
    value = fields.Float(
        digits=(16, 4),
        help="The observation a measured dimension banded; empty for a catalog row.",
    )
    points = fields.Float(help="Points contributed by this source.")
    max_points = fields.Float(
        help="Ceiling of the group this row belongs to: the attribute's, or the "
        "measured dimension's weight."
    )
    applied = fields.Boolean(
        default=True,
        help="Unchecked when the aggregation mode discarded this contribution "
        "(e.g. not the highest value under 'max'). A discarded row is still "
        "part of its group's ceiling.",
    )
    applicable = fields.Boolean(
        default=True,
        help="Unchecked when a dimension that skips missing observations had "
        "nothing to measure: the row explains the absence and its group leaves "
        "the denominator.",
    )
    note = fields.Char(compute="_compute_note")

    _SCORE_ROW_KEY = ("subject_id", "dimension_id", "source_key")
    _SCORE_ROW_VALUES = (
        "grouping_key",
        "value",
        "points",
        "max_points",
        "applied",
        "applicable",
    )

    def _score_host(self, dimension):
        return self.env[dimension.scorecard_id.res_model]

    @api.depends("dimension_id", "source_key")
    @api.depends_context("lang")
    def _compute_source_ref(self):
        keys_by_dimension = defaultdict(set)
        for row in self:
            keys_by_dimension[row.dimension_id].add(row.source_key)
        labels = {
            dimension: self._score_host(dimension)._score_labels(dimension, keys)
            for dimension, keys in keys_by_dimension.items()
        }
        for row in self:
            row.source_ref = labels[row.dimension_id].get(
                row.source_key, row.source_key
            )

    @api.depends("dimension_id", "source_key", "applied", "applicable")
    @api.depends_context("lang")
    def _compute_note(self):
        for row in self:
            row.note = self._score_host(row.dimension_id)._score_row_note(
                row.dimension_id, row.source_key, row.applied, row.applicable
            )

    @api.model
    def _reconcile_rows(self, subjects, rows):
        score_model = self.env(su=True)[self._name]
        existing = score_model.search([("subject_id", "in", subjects.ids)])

        by_key = {}
        for row in existing:
            key = (row.subject_id.id, row.dimension_id.id, row.source_key)
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
                if name in vals and row[name] != vals[name]
            }
            if changed:
                row.write(changed)

        stale = existing.filtered(lambda row: row.id not in matched_ids)
        if stale:
            stale.unlink()
        if to_create:
            score_model.create(to_create)
