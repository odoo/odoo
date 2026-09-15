from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.base.models.mixin_catalog import name_uniq_index


class MixinAttributeValue(models.AbstractModel):
    """Reusable base for an EAV attribute value."""

    # Concrete models add the attribute_id Many2one to their own attribute
    # model. The name-uniqueness rule mixin.catalog declares is re-scoped to it
    # below rather than left global: "Large" belongs to Size and to Format
    # independently, and only a duplicate *within* one attribute is a mistake.
    _name = "mixin.attribute.value"
    _inherit = ["mixin.catalog", "mixin.color"]
    _description = "Attribute Value Mixin"
    _order = "sequence, name"

    sequence = fields.Integer(default=10)
    color = fields.Integer(default=lambda self: self._default_color())

    _name_src_uniq = name_uniq_index(
        "attribute_id",
        message="A value with this name already exists for this attribute.",
    )

    @api.depends("attribute_id")
    @api.depends_context("show_attribute")
    def _compute_display_name(self):
        """Qualify a value with its attribute.

        A bare value name is ambiguous wherever values of different attributes
        meet -- "Large" or "High" says nothing on its own. The exception is a
        form that already groups values under their attribute (an attribute's
        own value list, a line being configured), which passes
        ``show_attribute=False`` to suppress the repetition.
        """
        if not self.env.context.get("show_attribute", True):
            return super()._compute_display_name()
        for value in self:
            value.display_name = f"{value.attribute_id.name}: {value.name}"
        return None

    # ------------------------------------------------------------
    # USAGE
    # ------------------------------------------------------------

    def _line_model_name(self):
        """Resolve the line model through the attribute this value belongs to.

        Read off ``attribute_id``'s comodel rather than asking consumers to
        repeat ``_attribute_line_model`` here: a value model always knows its
        attribute model, and one source of truth cannot drift from the other.

        :return: the line model's name, or None when the consumer set none
        """
        field = self._fields.get("attribute_id")
        if not field or not field.comodel_name:
            return None
        return self.env[field.comodel_name]._attribute_line_model

    def _filtered_used(self):
        """Return the subset of ``self`` already chosen on some attribute line.

        Consumers with a narrower notion of in-use override this -- product
        only counts lines of *active* templates.

        :return: the values that are in use
        """
        line_model = self._line_model_name()
        if not line_model:
            return self.browse()
        lines = self.env[line_model].search([("value_ids", "in", self.ids)])
        return lines.value_ids & self

    def _usage_label(self):
        """Name where these values are in use, for error messages.

        :return: human-readable list of subjects, or ""
        """
        return ""

    def _in_use_message(self):
        """Explain that these values are in use, or return False.

        Split out from the guard so a consumer can surface the same sentence
        without provoking the error -- product's value list asks for it over
        RPC to grey out the delete button.

        :return: the message, or False when nothing is in use
        """
        used = self._filtered_used()
        if not used:
            return False
        names = ", ".join(used.mapped("display_name"))
        usage = used._usage_label()
        return (
            self.env._(
                "You cannot delete the value %(names)s because it is used "
                "on: %(usage)s",
                names=names,
                usage=usage,
            )
            if usage
            else self.env._(
                "You cannot delete the value %(names)s because it is still in use.",
                names=names,
            )
        )

    # ------------------------------------------------------------
    # CRUD METHODS
    # ------------------------------------------------------------

    def write(self, vals):
        """Refuse to re-home a value that a subject already carries.

        The lines holding it point at the value, not at the pair, so moving it
        under another attribute leaves every one of them stray -- a violation
        of ``attribute.line.mixin._check_values`` that the line-side constraint
        cannot see, because the write lands on the value.
        """
        if "attribute_id" in vals:
            moved = self.filtered(lambda v: v.attribute_id.id != vals["attribute_id"])
            used = moved._filtered_used()
            if used:
                names = ", ".join(used.mapped("display_name"))
                usage = used._usage_label()
                raise UserError(
                    self.env._(
                        "You cannot change the attribute of %(names)s because "
                        "it is used on: %(usage)s",
                        names=names,
                        usage=usage,
                    )
                    if usage
                    else self.env._(
                        "You cannot change the attribute of %(names)s because "
                        "it is still in use.",
                        names=names,
                    )
                )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_in_use(self):
        """Refuse to delete a value some subject has already been given."""
        if message := self._in_use_message():
            raise UserError(message)
