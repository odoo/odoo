import json
import math
import logging
import re
from collections import Counter

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


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
    embedding_provider = fields.Char(default="local_tfidf", readonly=True)
    embedding_model = fields.Char(default="builtin_sparse_v1", readonly=True)
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
    def _build_sparse_embedding(self, text, max_terms=256):
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        counts = Counter(tokens)
        most_common = counts.most_common(max_terms)
        norm = math.sqrt(sum(freq * freq for _, freq in most_common)) or 1.0
        return {token: (freq / norm) for token, freq in most_common}

    @api.model
    def _build_dense_embedding_langchain(self, text, model_name):
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except Exception as exc:
            raise RuntimeError(
                "Backend 'huggingface_langchain' requer pacote 'langchain-huggingface'."
            ) from exc

        icp = self.env["ir.config_parameter"].sudo()
        hf_token = (icp.get_param("gov_ai_ml.huggingface_api_key") or "").strip()
        model_kwargs = {"device": "cpu"}
        if hf_token:
            model_kwargs["token"] = hf_token

        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs,
            encode_kwargs={"normalize_embeddings": True},
        )
        vector = embeddings.embed_query(text or "")
        return [float(value) for value in (vector or [])]

    @api.model
    def _get_embedding_backend(self):
        icp = self.env["ir.config_parameter"].sudo()
        provider = (icp.get_param("gov_ai_ml.embedding_provider") or "local_tfidf").strip().lower()
        model_name = (
            icp.get_param("gov_ai_ml.embedding_model_name")
            or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        ).strip()
        if provider not in {"local_tfidf", "huggingface_langchain"}:
            provider = "local_tfidf"
        return provider, model_name

    @api.model
    def _build_embedding(self, text, max_terms=256):
        provider, model_name = self._get_embedding_backend()
        if provider == "huggingface_langchain":
            try:
                dense = self._build_dense_embedding_langchain(text, model_name)
                if dense:
                    return {"kind": "dense", "values": dense}, provider, model_name
            except Exception as exc:
                _logger.warning(
                    "Falha no embedding Hugging Face via LangChain; fallback local ativado: %s",
                    exc,
                )
        sparse = self._build_sparse_embedding(text, max_terms=max_terms)
        return {"kind": "sparse", "values": sparse}, "local_tfidf", "builtin_sparse_v1"

    @api.model
    def _normalize_embedding_payload(self, payload):
        if isinstance(payload, dict) and "kind" in payload and "values" in payload:
            kind = (payload.get("kind") or "").strip().lower()
            values = payload.get("values")
            if kind in {"dense", "sparse"}:
                return kind, values
        if isinstance(payload, list):
            return "dense", payload
        if isinstance(payload, dict):
            return "sparse", payload
        return "sparse", {}

    @api.model
    def _cosine_similarity_sparse(self, left, right):
        if not left or not right:
            return 0.0
        if len(left) > len(right):
            left, right = right, left
        return float(sum(float(weight) * float(right.get(token, 0.0)) for token, weight in left.items()))

    @api.model
    def _cosine_similarity_dense(self, left, right):
        if not left or not right:
            return 0.0
        size = min(len(left), len(right))
        if size <= 0:
            return 0.0
        dot = 0.0
        norm_left = 0.0
        norm_right = 0.0
        for idx in range(size):
            left_value = float(left[idx])
            right_value = float(right[idx])
            dot += left_value * right_value
            norm_left += left_value * left_value
            norm_right += right_value * right_value
        if not norm_left or not norm_right:
            return 0.0
        return float(dot / (math.sqrt(norm_left) * math.sqrt(norm_right)))

    @api.model
    def _cosine_similarity(self, left_payload, right_payload):
        left_kind, left_values = self._normalize_embedding_payload(left_payload)
        right_kind, right_values = self._normalize_embedding_payload(right_payload)
        if left_kind != right_kind:
            return 0.0
        if left_kind == "dense":
            return self._cosine_similarity_dense(left_values or [], right_values or [])
        return self._cosine_similarity_sparse(left_values or {}, right_values or {})

    @api.model
    def _ensure_vector_for_memory(self, memory):
        embedding_payload, provider, model_name = self._build_embedding(memory.content_text or "")
        _kind, values = self._normalize_embedding_payload(embedding_payload)
        embedding_dim = len(values or [])
        vals = {
            "memory_id": memory.id,
            "text_hash": memory.content_hash or "",
            "embedding_json": json.dumps(embedding_payload, ensure_ascii=False),
            "embedding_dim": embedding_dim,
            "embedding_provider": provider,
            "embedding_model": model_name,
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
        target_provider, target_model = self._get_embedding_backend()
        domain = [("active", "=", True)]
        if company_id:
            domain.append(("company_id", "=", company_id))
        memories = Memory.search(domain, limit=max(1, int(limit or 1000)))
        refreshed = 0
        for memory in memories:
            vector = self.search([("memory_id", "=", memory.id)], limit=1)
            needs_refresh = (not vector) or (vector.text_hash != (memory.content_hash or ""))
            if vector and not needs_refresh:
                needs_refresh = (
                    (vector.embedding_provider or "") != target_provider
                    or (vector.embedding_model or "") != target_model
                )
            if needs_refresh:
                self._ensure_vector_for_memory(memory)
                refreshed += 1
        return refreshed

    @api.model
    def cron_refresh_embeddings(self):
        self.refresh_for_company(company_id=False, limit=3000)
        return True

    @api.model
    def search_relevant_scored(self, company_id, query, limit=10):
        query_embedding, _provider, _model = self._build_embedding(query or "")
        _q_kind, q_values = self._normalize_embedding_payload(query_embedding)
        if not q_values:
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
