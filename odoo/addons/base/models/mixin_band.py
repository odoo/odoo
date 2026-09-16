from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MixinBand(models.AbstractModel):
    _name = "mixin.band"
    _description = "Numeric Band Mixin"

    min_value = fields.Float(
        default=0.0,
        help="Lower bound of the band, inclusive.",
    )
    max_value = fields.Float(
        default=0.0,
        help="Upper bound of the band, exclusive -- it is the lower bound of "
        "the next band. 0 means no upper limit, which the highest band of a "
        "scale should use so nothing falls off the top.",
    )
    active = fields.Boolean(default=True)

    def _is_band(self):
        return True

    def _get_domain_band_scope(self):
        self.check_singleton()
        return []

    @staticmethod
    def _is_range_overlapping(band_a, band_b):
        max_a = band_a.max_value or float("inf")
        max_b = band_b.max_value or float("inf")
        return band_a.min_value < max_b and band_b.min_value < max_a

    def _is_covering(self, value):
        self.check_singleton()
        upper = self.max_value or float("inf")
        return self.min_value <= value < upper

    @api.constrains("min_value", "max_value", "active")
    def _check_band(self):
        scales = defaultdict(self.browse)
        for record in self:
            if not record._is_band():
                if record.min_value or record.max_value:
                    _debug.logic(
                        "band_rejected",
                        model=self._name,
                        record=record.id,
                        reason="bounds_on_non_band",
                    )
                    raise ValidationError(
                        self.env._(
                            "%(name)s: bounds only apply to a band.",
                            name=record.display_name,
                        )
                    )
                continue
            if record.min_value < 0:
                _debug.logic(
                    "band_rejected",
                    model=self._name,
                    record=record.id,
                    reason="negative_lower_bound",
                )
                raise ValidationError(
                    self.env._(
                        "%(name)s: the lower bound cannot be negative.",
                        name=record.display_name,
                    )
                )
            if record.max_value and record.max_value <= record.min_value:
                _debug.logic(
                    "band_rejected",
                    model=self._name,
                    record=record.id,
                    reason="upper_not_above_lower",
                )
                raise ValidationError(
                    self.env._(
                        "%(name)s: the upper bound (%(max)s) must be greater "
                        "than the lower bound (%(min)s), or zero for an "
                        "open-ended band.",
                        name=record.display_name,
                        max=record.max_value,
                        min=record.min_value,
                    )
                )
            if not record.active:
                continue
            scales[repr(record._get_domain_band_scope())] |= record

        _debug.pipeline(
            "band_overlap_check",
            model=self._name,
            records=len(self),
            scales=len(scales),
        )
        for records in scales.values():
            candidates = records.search(records[0]._get_domain_band_scope())
            _debug.perf.count(
                "band_scale_candidates", model=self._name, candidates=len(candidates)
            )
            for record in records:
                for other in candidates:
                    if other == record or not other._is_band():
                        continue
                    if record._is_range_overlapping(record, other):
                        _debug.logic(
                            "band_rejected",
                            model=self._name,
                            record=record.id,
                            other=other.id,
                            reason="overlap",
                        )
                        raise ValidationError(
                            self.env._(
                                "%(a)s overlaps with %(b)s.",
                                a=record.display_name,
                                b=other.display_name,
                            )
                        )
