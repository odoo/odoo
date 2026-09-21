from odoo import api, fields, models

KEYTERM_LIMIT = 100


class SpeechVocabulary(models.Model):
    _name = "speech.vocabulary"
    _description = "Speech Vocabulary"
    _order = "sequence, name"

    name = fields.Char(required=True)
    kind = fields.Selection(
        selection=[
            ("term", "Term"),
            ("product", "Product"),
            ("person", "Person"),
            ("place", "Place"),
            ("company", "Company"),
        ],
        default="term",
        required=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        help="Empty means every company",
    )

    _name_company_unique = models.Constraint(
        "UNIQUE NULLS NOT DISTINCT (name, company_id)",
        "A vocabulary term is already registered for this company.",
    )

    @api.model
    def _keyterms(self, company=None, limit=KEYTERM_LIMIT) -> list[str]:
        company = company or self.env.company
        return (
            self.sudo()
            .search([("company_id", "in", (company.id, False))], limit=limit)
            .mapped("name")
        )
