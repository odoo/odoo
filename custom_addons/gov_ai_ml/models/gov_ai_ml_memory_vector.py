import json
import math
import re
from collections import Counter

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GovAiMlMemoryVector(models.Model):
    _name = "gov.ai.ml.memory.vector"
    _description = "Vetor de Memoria IA"
    _order = "updated_at desc, id desc"

    _TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)

    memory_id = fields.Many2one(
        "gov.ai.memory",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="memory_id.company_id",
        store=True,
        readonly=True,
    )
    text_hash = fields.Char(required=True, index=True)
    embedding_json = fields.Text(required=True)
    embedding_dim = fields.Integer(default=0, readonly=True)
    updated_at = fields.Datetime(default=fields.Datetime.now, readonly=True)

    @api.constrains("memory_id")
    def _check_unique_memory_id(self):
        for rec in self:
            duplicate = self.search(
                [
                    ("id", "!=", rec.id),
                    ("memory_id", "=", rec.memory_id.id),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError("Ja existe vetor para esta memoria.")

    @api.model
    def _tokenize(self, text):
        return self._TOKEN_RE.findall((text or "").lower())

    @api.model
    def _build_embedding(self, text, max_terms=256):
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        counts = Counter(tokens)
        most_common = counts.most_common(max_terms)
        norm = math.sqrt(sum(freq * freq for _, freq in most_common)) or 1.0
        return {token: (freq / norm) for token, freq in most_common}

    @api.model
    def _cosine_similarity(self, left, right):
        if not left or not right:
            return 0.0
        if len(left) > len(right):
            left, right = right, left
        return float(sum(float(weight) * float(right.get(token, 0.0)) for token, weight in left.items()))

    @api.model
    def _ensure_vector_for_memory(self, memory):
        embedding = self._build_embedding(memory.content_text or "")
        vals = {
            "memory_id": memory.id,
            "text_hash": memory.content_hash or "",
            "embedding_json": json.dumps(embedding, ensure_ascii=False),
            "embedding_dim": len(embedding),
            "updated_at": fields.Datetime.now(),
        }
        existing = self.search([("memory_id", "=", memory.id)], limit=1)
        if existing:
            existing.write(vals)
            return existing
        return self.create(vals)

    @api.model
    def refresh_for_company(self, company_id=None, limit=1000):
        Memory = self.env["gov.ai.memory"].sudo()
        domain = [("active", "=", True)]
        if company_id:
            domain.append(("company_id", "=", company_id))
        memories = Memory.search(domain, limit=max(1, int(limit or 1000)))
        refreshed = 0
        for memory in memories:
            vector = self.search([("memory_id", "=", memory.id)], limit=1)
            if (not vector) or (vector.text_hash != (memory.content_hash or "")):
                self._ensure_vector_for_memory(memory)
                refreshed += 1
        return refreshed

    @api.model
    def cron_refresh_embeddings(self):
        self.refresh_for_company(company_id=False, limit=3000)
        return True

    @api.model
    def search_relevant_scored(self, company_id, query, limit=10):
        query_embedding = self._build_embedding(query or "")
        if not query_embedding:
            return []
        vectors = self.search([("company_id", "=", company_id)])
        scored = []
        for vector in vectors:
            try:
                candidate_embedding = json.loads(vector.embedding_json or "{}")
            except Exception:
                candidate_embedding = {}
            score = self._cosine_similarity(query_embedding, candidate_embedding)
            if score > 0:
                scored.append((vector.memory_id.id, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[: max(1, int(limit or 10))]
