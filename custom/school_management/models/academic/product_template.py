from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_textbook = fields.Boolean(
        string="Is Textbook",
        default=False,
        index=True,
        help="Check this box if this product is an academic textbook.",
    )
    isbn = fields.Char(
        string="ISBN",
        copy=False,
        index=True,
        help="International Standard Book Number.",
    )
    author = fields.Char(string="Author")
    publisher = fields.Char(string="Publisher")
    edition = fields.Char(string="Edition")
    subject_link_ids = fields.One2many(
        "university.subject.book",
        "product_tmpl_id",
        string="Subject Links",
    )
    subject_count = fields.Integer(
        string="Subject Count",
        compute="_compute_subject_count",
    )

    _unique_isbn = models.Constraint(
        "UNIQUE(isbn)",
        "The ISBN must be unique when set.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "isbn" in vals and isinstance(vals["isbn"], str) and not vals["isbn"].strip():
                vals["isbn"] = False
        return super().create(vals_list)

    def write(self, vals):
        if "isbn" in vals and isinstance(vals["isbn"], str) and not vals["isbn"].strip():
            vals["isbn"] = False
        return super().write(vals)

    @api.depends("subject_link_ids")
    def _compute_subject_count(self):
        for rec in self:
            rec.subject_count = len(rec.subject_link_ids)

    def action_view_subjects(self):
        self.ensure_one()
        subject_ids = self.subject_link_ids.mapped("subject_id").ids
        return {
            "name": f"Subjects - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "university.subject",
            "view_mode": "list,kanban,form",
            "domain": [("id", "in", subject_ids)],
        }
