# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models
from odoo.tools.sql import SQL

_logger = logging.getLogger(__name__)


class WebsiteSequenceMixin(models.AbstractModel):
    _name = "website.sequence.mixin"
    _description = "Website Sequence Mixin"

    # === DEFAULT METHODS ===#

    @api.model
    def _default_website_sequence(self):
        self.env.cr.execute(
            SQL("SELECT MAX(website_sequence) FROM %s", SQL.identifier(self._table))
        )
        max_sequence = self.env.cr.fetchone()[0]
        if max_sequence is None:
            return 10000
        return max_sequence + 5

    # === FIELDS ===#

    website_sequence = fields.Integer(
        string="Website Sequence",
        help="Determine the display order in the Website eCommerce",
        default=_default_website_sequence,
        init_storage="_init_column_website_sequence",
        copy=False,
        index=True,
    )

    # === SEQUENCE METHODS ===#

    def _init_column_website_sequence(self):
        # Seed a unique website_sequence per row instead of one shared default,
        # generating the running values in SQL (row_number) in a single statement.
        _logger.debug(
            "Table '%s': setting default value of new column %s to unique values for each row",
            self._table,
            "website_sequence",
        )
        self.env.cr.execute(
            SQL(
                """
            UPDATE %(table)s AS t
               SET website_sequence = seq.value
              FROM (
                  SELECT id,
                         %(start)s + (row_number() OVER (ORDER BY id) - 1) * 5 AS value
                    FROM %(table)s
                   WHERE website_sequence IS NULL
              ) AS seq
             WHERE t.id = seq.id
            """,
                table=SQL.identifier(self._table),
                start=self._default_website_sequence(),
            )
        )

    def set_sequence_top(self):
        min_sequence = self.sudo().search([], order="website_sequence ASC", limit=1)
        self.website_sequence = min_sequence.website_sequence - 5

    def set_sequence_bottom(self):
        max_sequence = self.sudo().search([], order="website_sequence DESC", limit=1)
        self.website_sequence = max_sequence.website_sequence + 5

    def set_sequence_up(self):
        previous_record = self.sudo().search(
            [
                ("website_sequence", "<", self.website_sequence),
                ("website_published", "=", self.website_published),
            ],
            order="website_sequence DESC",
            limit=1,
        )
        if previous_record:
            previous_record.website_sequence, self.website_sequence = (
                self.website_sequence,
                previous_record.website_sequence,
            )
        else:
            self.set_sequence_top()

    def set_sequence_down(self):
        next_record = self.sudo().search(
            [
                ("website_sequence", ">", self.website_sequence),
                ("website_published", "=", self.website_published),
            ],
            order="website_sequence ASC",
            limit=1,
        )
        if next_record:
            next_record.website_sequence, self.website_sequence = (
                self.website_sequence,
                next_record.website_sequence,
            )
        else:
            self.set_sequence_bottom()
