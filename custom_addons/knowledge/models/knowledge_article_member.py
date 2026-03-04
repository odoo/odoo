from odoo import api, fields, models


class KnowledgeArticleMember(models.Model):
    _name = "knowledge.article.member"
    _description = "Knowledge Article Member"
    _order = "id"

    article_id = fields.Many2one(
        "knowledge.article",
        required=True,
        index=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        index=True,
        ondelete="cascade",
    )
    permission = fields.Selection(
        [("read", "Read"), ("write", "Write")],
        required=True,
        default="read",
        index=True,
    )

    _knowledge_article_member_unique = models.Constraint(
        "unique(article_id, partner_id)",
        "This partner is already a member of the article.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped("article_id")._check_user_can_write()
        return records

    def write(self, vals):
        self.mapped("article_id")._check_user_can_write()
        return super().write(vals)

    def unlink(self):
        self.mapped("article_id")._check_user_can_write()
        return super().unlink()
