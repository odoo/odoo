import hashlib
import re

from odoo import api, fields, models


class GovAiMemory(models.Model):
    _name = "gov.ai.memory"
    _description = "Memória Persistente de IA por UG"
    _order = "company_id, last_used_at desc, id desc"

    _TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Unidade Gestora",
        required=True,
        default=lambda self: self.env.company,
    )
    source_type = fields.Selection(
        [
            ("manual", "Manual"),
            ("upload", "Upload"),
            ("process_doc", "Documento do Processo"),
            ("outro", "Outro"),
        ],
        default="manual",
        required=True,
    )
    source_model = fields.Char(string="Modelo de Origem")
    source_res_id = fields.Integer(string="ID de Origem")
    tags = fields.Char(help="Etiquetas separadas por vírgula")
    content_text = fields.Text(required=True)
    content_hash = fields.Char(string="Hash SHA-256", readonly=True, index=True)
    upload_file = fields.Binary(string="Arquivo de Origem", attachment=True)
    upload_filename = fields.Char()
    created_by = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        readonly=True,
    )
    last_used_at = fields.Datetime(readonly=True)
    use_count = fields.Integer(default=0, readonly=True)
    word_count = fields.Integer(compute="_compute_word_count", store=True)

    @api.depends("content_text")
    def _compute_word_count(self):
        for rec in self:
            rec.word_count = len(self._TOKEN_RE.findall((rec.content_text or "").lower()))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            text = vals.get("content_text") or ""
            vals["content_hash"] = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if "content_text" in vals:
            text = vals.get("content_text") or ""
            vals["content_hash"] = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
        return super().write(vals)

    @api.model
    def _score_text(self, query_tokens, candidate_text):
        if not query_tokens:
            return 0
        candidate_tokens = self._TOKEN_RE.findall((candidate_text or "").lower())
        if not candidate_tokens:
            return 0
        token_set = set(candidate_tokens)
        score = sum(1 for token in query_tokens if token in token_set)
        return score

    @api.model
    def search_relevant(self, company_id, query, limit=5):
        memories = self.search(
            [
                ("active", "=", True),
                ("company_id", "=", company_id),
            ]
        )
        query_tokens = self._TOKEN_RE.findall((query or "").lower())
        scored = []
        for memory in memories:
            score = self._score_text(query_tokens, memory.content_text)
            if score > 0:
                scored.append((score, memory.id))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        top_ids = [memory_id for _, memory_id in scored[: max(1, int(limit or 5))]]
        if not top_ids:
            return self.browse()
        ordered = self.browse(top_ids)
        # Mantém a ordenação por relevância.
        ordered = ordered.sorted(key=lambda rec: top_ids.index(rec.id))
        return ordered

    def mark_used(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.sudo().write(
                {
                    "last_used_at": now,
                    "use_count": rec.use_count + 1,
                }
            )
