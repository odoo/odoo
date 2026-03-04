from odoo import fields, models


class KnowledgeArticleFavorite(models.Model):
    _name = "knowledge.article.favorite"
    _description = "Knowledge Article Favorite"
    _order = "sequence, id"

    article_id = fields.Many2one(
        "knowledge.article",
        required=True,
        index=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        "res.users",
        required=True,
        index=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)

    _knowledge_article_favorite_unique = models.Constraint(
        "unique(article_id, user_id)",
        "The article is already favorited by this user.",
    )
