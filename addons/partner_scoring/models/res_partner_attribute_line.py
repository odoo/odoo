import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResPartnerAttributeLine(models.Model):
    _name = "res.partner.attribute.line"
    _inherit = "mixin.attribute.line"
    _description = "Contact Attribute Line"
    _order = "attribute_id, id"
    _rec_name = "attribute_id"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        index=True,
        required=True,
        ondelete="cascade",
    )
    attribute_id = fields.Many2one(
        comodel_name="res.partner.attribute",
        index=True,
        required=True,
        ondelete="restrict",
    )
    value_ids = fields.Many2many(
        comodel_name="res.partner.attribute.value",
        relation="res_partner_attribute_line_value_rel",
        column1="line_id",
        column2="value_id",
        string="Values",
        domain="[('attribute_id', '=', attribute_id)]",
    )

    _partner_attribute_uniq = models.Constraint(
        "UNIQUE(partner_id, attribute_id)",
        "This attribute is already set for the partner.",
    )

    _SCORE_TRIGGERS = ("partner_id", "attribute_id", "value_ids", "active")

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.partner_id._update_profile_scores()
        return lines

    def write(self, vals):
        if not any(name in vals for name in self._SCORE_TRIGGERS):
            return super().write(vals)
        partners_before = self.partner_id
        result = super().write(vals)
        (partners_before | self.partner_id)._update_profile_scores()
        return result

    def unlink(self):
        partners = self.partner_id
        result = super().unlink()
        partners._update_profile_scores()
        return result

    @api.constrains("partner_id")
    def _check_commercial_partner(self):
        for line in self:
            partner = line.partner_id
            if partner != partner.commercial_partner_id:
                raise ValidationError(
                    self.env._(
                        "Profile attributes can only be set on the commercial "
                        "entity %(commercial)s, not on its contact %(contact)s.",
                        commercial=partner.commercial_partner_id.display_name,
                        contact=partner.display_name,
                    )
                )

    @api.model
    def _follow_commercial_partner(self, partners):
        """Move captured attributes up when the contact hierarchy moves.

        _check_commercial_partner is an @api.constrains on the line's
        partner_id, and the ORM has no cross-model constrains: nothing re-runs
        it when the *partner* is demoted to a contact. The lines would keep
        scoring a record that is no longer the commercial entity while the new
        one scores as if nothing had ever been captured. Moving them is
        preferred over rejecting the move, which would block a legitimate
        hierarchy edit for a reason the user cannot act on.
        """
        line_model = self.with_context(active_test=False)
        for partner in partners:
            commercial = partner.commercial_partner_id
            if commercial == partner:
                continue
            stray = line_model.search([("partner_id", "=", partner.id)])
            if not stray:
                continue
            taken = set(
                line_model.search([("partner_id", "=", commercial.id)]).attribute_id.ids
            )
            movable = stray.filtered(
                lambda line, taken=taken: line.attribute_id.id not in taken
            )
            if movable:
                movable.partner_id = commercial
            blocked = stray - movable
            if blocked:
                _logger.warning(
                    "partner_scoring: %s moved under %s but keeps %s captured "
                    "attribute(s) the commercial entity already answers: %s",
                    partner.display_name,
                    commercial.display_name,
                    len(blocked),
                    ", ".join(sorted(blocked.attribute_id.mapped("name"))),
                )
