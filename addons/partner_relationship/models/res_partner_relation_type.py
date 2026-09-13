from odoo import api, fields, models
from odoo.exceptions import ValidationError

CATEGORY_SELECTION = [
    ("blood", "Consanguinity"),
    ("affinity", "Affinity"),
    ("ritual", "Ritual kinship"),
    ("household", "Household"),
    ("business", "Business"),
    ("agricultural", "Agricultural"),
]


class ResPartnerRelationType(models.Model):
    _name = "res.partner.relation.type"
    _description = "Partner Relationship Type"
    _order = "category, sequence, id"

    code = fields.Char(
        copy=False,
        required=True,
    )
    name = fields.Char(
        translate=True,
        required=True,
    )
    name_inverse = fields.Char(translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    name_male = fields.Char(translate=True)
    name_female = fields.Char(translate=True)
    name_inverse_male = fields.Char(translate=True)
    name_inverse_female = fields.Char(translate=True)

    is_symmetric = fields.Boolean(
        help="The relationship reads the same from both ends: sibling, cousin,"
        " compadre, business partner."
    )
    is_antisymmetric = fields.Boolean(
        help="The relationship cannot hold in both directions: if one contact is"
        " the parent of another, the reverse is impossible. Leave off for a tie"
        " that can genuinely be mutual, such as cross-shareholding or a"
        " reciprocal guarantee."
    )
    category = fields.Selection(
        selection=CATEGORY_SELECTION,
        default="blood",
        required=True,
    )
    degree = fields.Integer(
        default=0,
        help="Civil-law kinship distance. Zero for a tie that carries no"
        " genealogical distance, such as a compadre or a business partner.",
    )
    weight_risk = fields.Float(
        default=0.0,
        help="How strongly this tie implies a shared economic interest, from 0"
        " to 1. Consumed by the credit and compliance bridges.",
    )

    count_relation = fields.Integer(compute="_compute_count_relation")

    _code_uniq = models.Constraint(
        "UNIQUE(code)",
        "A relationship type with this code already exists.",
    )
    _weight_risk_range = models.Constraint(
        "CHECK(weight_risk >= 0 AND weight_risk <= 1)",
        "The risk weight must be between 0 and 1.",
    )
    _degree_positive = models.Constraint(
        "CHECK(degree >= 0)",
        "The kinship degree cannot be negative.",
    )

    @api.constrains("is_symmetric", "is_antisymmetric", "name")
    def _check_symmetry_exclusive(self):
        for relation_type in self:
            if relation_type.is_symmetric and relation_type.is_antisymmetric:
                raise ValidationError(
                    self.env._(
                        "%s cannot be both symmetric and antisymmetric.",
                        relation_type.name,
                    )
                )

    @api.constrains("is_symmetric", "name_inverse", "name")
    def _check_name_inverse(self):
        for relation_type in self:
            if not relation_type.is_symmetric and not relation_type.name_inverse:
                raise ValidationError(
                    self.env._(
                        "%s is not symmetric, so it needs a wording for the"
                        " other end of the relationship.",
                        relation_type.name,
                    )
                )

    def write(self, vals):
        result = super().write(vals)
        self.env["res.partner"]._invalidate_relation_graph()
        return result

    def _compute_count_relation(self):
        counts = dict(
            self.env["res.partner.relation"]._read_group(
                [("type_id", "in", self.ids)], ["type_id"], ["__count"]
            )
        )
        for relation_type in self:
            relation_type.count_relation = counts.get(relation_type, 0)

    def action_view_relations(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": "res.partner.relation",
            "view_mode": "list,form",
            "domain": [("type_id", "=", self.id)],
            "context": {"default_type_id": self.id},
        }

    def _get_label(self, is_inverse=False, gender=None):
        self.check_singleton()
        if is_inverse and not self.is_symmetric:
            gendered = {
                "male": self.name_inverse_male,
                "female": self.name_inverse_female,
            }
            return gendered.get(gender) or self.name_inverse or self.name
        gendered = {"male": self.name_male, "female": self.name_female}
        return gendered.get(gender) or self.name
