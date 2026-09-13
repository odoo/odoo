from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MixinAttributeLine(models.AbstractModel):
    """Reusable base for an attribute line (one attribute + its chosen values)."""

    # Concrete models declare the parent Many2one (e.g. product_tmpl_id,
    # partner_id, surface_id), attribute_id and value_ids with their concrete
    # comodels and domains. This mixin owns the shared shape and the coherence
    # validation.
    _name = "mixin.attribute.line"
    _description = "Attribute Line Mixin"
    _order = "sequence, attribute_id, id"
    # _rec_name is deliberately NOT set here: attribute_id is declared by the
    # concrete model, and the ORM validates _rec_name against the fields the
    # abstract model itself declares. Concrete models set _rec_name themselves.

    # Whether a line is meaningless without values. True where the line *is*
    # the offer, so an empty one says nothing (a product template offering an
    # attribute with no values). False where a line legitimately exists before
    # it is filled in -- a surface or a partner may carry the attribute as a
    # slot awaiting capture.
    _requires_value = False

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    value_count = fields.Count(
        count_of="value_ids",
        store=True,
    )

    def _subject_label(self):
        """Name the record this line hangs off, for error messages.

        Empty by default: on most subjects the offending line is obvious from
        the record being saved. Concrete models whose users need disambiguating
        (one product template among thousands) override this to return e.g.
        ``self.product_tmpl_id.display_name``.
        """
        return ""

    @api.constrains("active", "attribute_id", "value_ids")
    def _check_values(self):
        """Values must belong to the attribute; single attributes allow one.

        Note this is an ``@api.constrains`` on the *line*: it cannot see a
        change made to the attribute itself. ``mixin.attribute`` re-runs it
        from its own ``write`` when ``value_type`` moves -- see
        ``attribute.mixin._attribute_line_model``.
        """
        for line in self:
            attribute = line.attribute_id.display_name
            subject = line._subject_label()

            if line._requires_value and line.active and not line.value_ids:
                raise ValidationError(
                    self.env._(
                        "The attribute %(attr)s must have at least one value "
                        "for %(subject)s.",
                        attr=attribute,
                        subject=subject,
                    )
                    if subject
                    else self.env._(
                        "The attribute %(attr)s must have at least one value.",
                        attr=attribute,
                    )
                )

            stray = line.value_ids.filtered(
                lambda v, line=line: v.attribute_id != line.attribute_id
            )
            if stray:
                values = ", ".join(stray.mapped("display_name"))
                raise ValidationError(
                    self.env._(
                        "On %(subject)s you cannot associate the values "
                        "%(values)s with the attribute %(attr)s because they "
                        "do not match.",
                        subject=subject,
                        values=values,
                        attr=attribute,
                    )
                    if subject
                    else self.env._(
                        "Values %(values)s do not belong to attribute %(attr)s.",
                        values=values,
                        attr=attribute,
                    )
                )

            if line.attribute_id.value_type == "single" and len(line.value_ids) > 1:
                raise ValidationError(
                    self.env._(
                        "The attribute %(attr)s accepts a single value "
                        "for %(subject)s.",
                        attr=attribute,
                        subject=subject,
                    )
                    if subject
                    else self.env._(
                        "Attribute %(attr)s accepts a single value.",
                        attr=attribute,
                    )
                )
