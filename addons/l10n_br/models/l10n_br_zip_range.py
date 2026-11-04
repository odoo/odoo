# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class L10nBrZipRange(models.Model):
    _name = "l10n_br.zip.range"
    _description = "Brazilian city zip range"

    city_id = fields.Many2one("res.city", string="City", required=True)
    start = fields.Char(string="From", required=True)
    end = fields.Char(string="To", required=True)

    _sql_constraints = [
        ("uniq_start", "unique(start)", 'The "from" zip must be unique'),
        ("uniq_end", 'unique("end")', 'The "to" zip must be unique.'),
    ]

    @api.constrains("start", "end")
    def _check_range(self):
        zip_format = re.compile(r"\d{5}-\d{3}")
        for zip_range in self:
            if not zip_format.fullmatch(zip_range.start) or not zip_format.fullmatch(zip_range.end):
                raise ValidationError(
                    _(
                        "Invalid zip range format: %(start)s %(end)s. It should follow this format: 01000-001",
                        start=zip_range.start,
                        end=zip_range.end,
                    )
                )

            if zip_range.start >= zip_range.end:
                raise ValidationError(
                    _("Start should be less than end: %(start)s %(end)s", start=zip_range.start, end=zip_range.end)
                )
