from odoo import api, fields, models
from odoo.exceptions import UserError


class MixinAttribute(models.AbstractModel):
    """Reusable base for an EAV attribute (the dimension being profiled)."""

    # Concrete models inherit this mixin and add their own value_ids One2many
    # pointing to the matching concrete value model. Extend value_type or
    # display_type with selection_add if the subject needs extra modes.
    #
    # ``name``, ``active`` and the unscoped name-uniqueness rule come from
    # ``mixin.catalog``. The rule is kept here rather than declined, because
    # whether two attributes may share a name is a property of the subject's
    # vocabulary and not of attributes as such: it is flat for agro's surface
    # and partner taxonomies, and not for product, which declines it on the
    # concrete model with ``no_name_uniq_index()``. Declining it *here* would
    # not merely leave the choice open -- an opt-out is a real definition that
    # wins the MRO over ``mixin.catalog``'s, so it would silently drop the
    # index from every consumer that wanted one.
    _name = "mixin.attribute"
    _inherit = ["mixin.catalog"]
    _description = "Attribute Mixin"
    _order = "sequence, name"

    # Concrete model carrying the lines that bind this attribute to a subject,
    # e.g. "product.template.attribute.line". Setting it enables two things:
    # a change of ``value_type`` re-validates the lines already using the
    # attribute, and the in-use guards below can see whether anything holds it.
    # Leaving it None disables both.
    #
    # The re-validation is needed because ``attribute.line.mixin._check_values``
    # is an ``@api.constrains`` on the *line* and the ORM has no cross-model
    # constrains: nothing re-runs it when the *attribute* moves. Without this,
    # flipping value_type from 'multi' to 'single' left every existing
    # multi-value line silently violating the very rule the constraint exists
    # to enforce -- the violation was reachable, just not by the write the
    # constraint watches.
    _attribute_line_model = None

    sequence = fields.Integer(default=10)
    value_type = fields.Selection(
        selection=[
            ("single", "Single value"),
            ("multi", "Multiple values"),
        ],
        default="single",
        required=True,
        help="How many values of this attribute a single line may hold. This "
        "is a data rule, orthogonal to display_type, which only picks the "
        "widget: a 'single' attribute may still render as radio, pills, "
        "select or colour swatches.",
    )
    display_type = fields.Selection(
        selection=[
            ("radio", "Radio"),
            ("pills", "Pills"),
            ("select", "Select"),
            ("color", "Color"),
            ("multi", "Multi-checkbox"),
            ("image", "Image"),
        ],
        default="radio",
        required=True,
        help="Widget used to pick values of this attribute.",
    )

    # ------------------------------------------------------------
    # USAGE
    # ------------------------------------------------------------

    def _filtered_used(self):
        """Return the subset of ``self`` already bound to a subject.

        "Bound" means some attribute line references it. Consumers with a
        narrower notion of in-use override this -- product only counts lines of
        *active* templates, so an attribute left over on an archived product
        stays deletable.

        :return: the attributes that are in use
        """
        if not self._attribute_line_model:
            return self.browse()
        lines = self.env[self._attribute_line_model].search(
            [("attribute_id", "in", self.ids)]
        )
        return lines.attribute_id & self

    def _usage_label(self):
        """Name where these attributes are in use, for error messages.

        Empty by default, which yields a shorter message. Concrete models
        override it to name the subjects holding them.

        :return: human-readable list of subjects, or ""
        """
        return ""

    # ------------------------------------------------------------
    # CRUD METHODS
    # ------------------------------------------------------------

    def write(self, vals):
        """Re-validate existing lines when the cardinality rule changes.

        See ``_attribute_line_model`` for why this cannot be an
        ``@api.constrains``.
        """
        result = super().write(vals)
        if "value_type" in vals and self._attribute_line_model:
            self.env[self._attribute_line_model].search(
                [("attribute_id", "in", self.ids)]
            )._check_values()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_in_use(self):
        """Refuse to delete an attribute a subject still carries.

        Deleting it would cascade its values away and take the captured lines
        with them -- silent data loss that no later pass can reconstruct.
        """
        used = self._filtered_used()
        if not used:
            return
        names = ", ".join(used.mapped("display_name"))
        usage = used._usage_label()
        raise UserError(
            self.env._(
                "You cannot delete the attribute %(names)s because it is used "
                "on: %(usage)s",
                names=names,
                usage=usage,
            )
            if usage
            else self.env._(
                "You cannot delete the attribute %(names)s because it is still in use.",
                names=names,
            )
        )

    def action_archive(self):
        """Refuse to archive an attribute a subject still carries.

        Archiving hides it from the pickers while the lines holding it stay
        live, so the records keep a value the configuration no longer offers.
        """
        used = self._filtered_used()
        if used:
            names = ", ".join(used.mapped("display_name"))
            usage = used._usage_label()
            raise UserError(
                self.env._(
                    "You cannot archive the attribute %(names)s because it is "
                    "used on: %(usage)s",
                    names=names,
                    usage=usage,
                )
                if usage
                else self.env._(
                    "You cannot archive the attribute %(names)s because it is "
                    "still in use.",
                    names=names,
                )
            )
        return super().action_archive()
