from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class ResPartnerRelation(models.Model):
    _name = "res.partner.relation"
    _description = "Partner Relationship"
    _order = "type_id, id"
    _rec_names_search = ["partner_id", "other_partner_id", "type_id"]

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        index=True,
        required=True,
        ondelete="cascade",
    )
    other_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Related Contact",
        index=True,
        required=True,
        ondelete="cascade",
    )

    type_id = fields.Many2one(
        comodel_name="res.partner.relation.type",
        string="Relationship",
        index=True,
        required=True,
    )
    category = fields.Selection(
        related="type_id.category",
    )
    degree = fields.Integer(
        related="type_id.degree",
    )
    weight_risk = fields.Float(
        related="type_id.weight_risk",
    )

    label = fields.Char(compute="_compute_labels")
    label_inverse = fields.Char(compute="_compute_labels")

    date_start = fields.Date()
    date_end = fields.Date()
    active = fields.Boolean(default=True)
    note = fields.Text()

    _partners_differ = models.Constraint(
        "CHECK(partner_id != other_partner_id)",
        "A contact cannot be related to itself.",
    )
    _relation_uniq = models.Constraint(
        "UNIQUE(partner_id, other_partner_id, type_id)",
        "This relationship is already recorded between these two contacts.",
    )

    @api.constrains("partner_id", "other_partner_id", "type_id", "active")
    def _check_no_mirror(self):
        relations = self.filtered(
            lambda rel: (
                rel.active
                and (rel.type_id.is_symmetric or rel.type_id.is_antisymmetric)
            )
        )
        if not relations:
            return
        # A mirror has its two ends swapped, so it can never be the record
        # itself, and the batch must not be excluded: two rows mirroring each
        # other inside one create are exactly what has to be caught.
        mirrors = self.search(
            Domain.OR(
                Domain("partner_id", "=", rel.other_partner_id.id)
                & Domain("other_partner_id", "=", rel.partner_id.id)
                & Domain("type_id", "=", rel.type_id.id)
                for rel in relations
            )
        )
        mirrored = {
            (mirror.other_partner_id.id, mirror.partner_id.id, mirror.type_id.id)
            for mirror in mirrors
        }
        for relation in relations:
            key = (
                relation.partner_id.id,
                relation.other_partner_id.id,
                relation.type_id.id,
            )
            if key not in mirrored:
                continue
            if relation.type_id.is_symmetric:
                raise ValidationError(
                    self.env._(
                        "%(type)s reads the same from both ends and is already"
                        " recorded between %(one)s and %(other)s.",
                        type=relation.type_id.name,
                        one=relation.partner_id.display_name,
                        other=relation.other_partner_id.display_name,
                    )
                )
            raise ValidationError(
                self.env._(
                    "%(other)s is already %(label)s %(one)s, so %(one)s cannot"
                    " also be %(label)s %(other)s.",
                    label=relation.type_id.name,
                    one=relation.partner_id.display_name,
                    other=relation.other_partner_id.display_name,
                )
            )

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for relation in self:
            if (
                relation.date_start
                and relation.date_end
                and relation.date_end < relation.date_start
            ):
                raise ValidationError(
                    self.env._("A relationship cannot end before it starts.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        relations = super().create(vals_list)
        self.env["res.partner"]._invalidate_relation_graph()
        return relations

    def write(self, vals):
        result = super().write(vals)
        self.env["res.partner"]._invalidate_relation_graph()
        return result

    def unlink(self):
        result = super().unlink()
        self.env["res.partner"]._invalidate_relation_graph()
        return result

    @api.depends(
        "type_id.name",
        "type_id.name_inverse",
        "type_id.name_male",
        "type_id.name_female",
        "type_id.name_inverse_male",
        "type_id.name_inverse_female",
        "type_id.is_symmetric",
        "partner_id.gender",
        "other_partner_id.gender",
    )
    def _compute_labels(self):
        for relation in self:
            # A record being composed in the form has no type yet, and the
            # onchange computes both labels before the user picks one.
            if not relation.type_id:
                relation.label = False
                relation.label_inverse = False
                continue
            relation.label = relation.type_id._get_label(
                gender=relation.partner_id.gender
            )
            relation.label_inverse = relation.type_id._get_label(
                is_inverse=True, gender=relation.other_partner_id.gender
            )

    @api.depends("label", "partner_id", "other_partner_id")
    def _compute_display_name(self):
        for relation in self:
            relation.display_name = self.env._(
                "%(one)s — %(label)s — %(other)s",
                one=relation.partner_id.display_name or "",
                label=relation.label or "",
                other=relation.other_partner_id.display_name or "",
            )

    def action_swap(self):
        for relation in self:
            relation.write(
                {
                    "partner_id": relation.other_partner_id.id,
                    "other_partner_id": relation.partner_id.id,
                }
            )

    def _get_label_from(self, partner):
        self.check_singleton()
        is_inverse = partner.id != self.partner_id.id
        subject = self.other_partner_id if is_inverse else self.partner_id
        return self.type_id._get_label(is_inverse=is_inverse, gender=subject.gender)

    # The graph is what is in force today: a tie whose end date has passed is
    # kept on the contact as history but reaches nobody.
    @api.model
    def _get_domain_touching(self, partner_ids):
        touching = Domain("partner_id", "in", partner_ids) | Domain(
            "other_partner_id", "in", partner_ids
        )
        return touching & self._get_domain_in_force()

    @api.model
    def _get_domain_in_force(self):
        return Domain("date_end", "=", False) | Domain(
            "date_end", ">=", fields.Date.context_today(self)
        )
