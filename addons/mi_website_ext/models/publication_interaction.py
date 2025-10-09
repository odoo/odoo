# mi_website_ext/models/publication_interaction.py
from odoo import models, fields, api


class PublicationComment(models.Model):
    _name = "publication.comment"
    _description = "Comentario de Publicación del Portal"
    _order = "create_date asc" 

    res_model = fields.Char(
        string="Modelo Relacionado", readonly=True, required=True, index=True
    )
    res_id = fields.Many2oneReference(
        string="Registro Relacionado", readonly=True, required=True, index=True
    )

    publication_id = fields.Many2one(
        "website.publication",
        string="Publicación",
        required=True,
        ondelete="cascade",
        index=True,
    )

    parent_id = fields.Many2one(
        "publication.comment", string="Comentario Padre", ondelete="cascade", index=True
    )
    child_ids = fields.One2many("publication.comment", "parent_id", string="Respuestas")

    content = fields.Text(string="Comentario", required=True)

    author_id = fields.Many2one("res.partner", string="Autor")
    like_ids = fields.One2many("publication.comment.like", "comment_id", string="Likes")
    like_count = fields.Integer(
        string="Total de Likes", compute="_compute_like_count", store=False
    )
    is_liked_by_current_user = fields.Boolean(
        string="Le gusta al usuario actual", compute="_compute_is_liked", store=False
    )

    @api.depends("like_ids")
    def _compute_like_count(self):
        for comment in self:
            comment.like_count = len(comment.like_ids)

    def _compute_is_liked(self):
        current_user_partner_id = self.env.user.partner_id.id
        for comment in self:
            existing_like = self.env["publication.comment.like"].search(
                [
                    ("comment_id", "=", comment.id),
                    ("partner_id", "=", current_user_partner_id),
                ],
                limit=1,
            )
            comment.is_liked_by_current_user = bool(existing_like)


class PublicationCommentLike(models.Model):
    _name = "publication.comment.like"
    _description = "Like en un Comentario de Publicación"

    comment_id = fields.Many2one(
        "publication.comment",
        string="Comentario",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Usuario (Partner)", required=True, ondelete="cascade"
    )

    _sql_constraints = [
        (
            "partner_comment_uniq",
            "unique(partner_id, comment_id)",
            "Solo puedes dar un like por comentario.",
        )
    ]
