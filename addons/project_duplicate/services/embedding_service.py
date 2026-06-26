import logging
import math
import time
import zlib
from odoo import fields
try:
    from odoo.tools.mail import html_to_inner_content
except ImportError:
    from odoo.tools import html_to_inner_content

_logger = logging.getLogger(__name__)

try:
    from fastembed import TextEmbedding
    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False
    _logger.warning("The 'fastembed' library is not installed. Duplicate task detection will be disabled.")


class EmbeddingService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance._model = None
        return cls._instance

    def _get_model(self):
        if not FASTEMBED_AVAILABLE:
            return None
        if self._model is None:
            try:
                # Load the model once
                self._model = TextEmbedding("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            except Exception as e:  # noqa: BLE001
                _logger.error("Failed to initialize fastembed model: %s", e)
        return self._model

    def normalize_vector(self, v):
        norm = math.sqrt(sum(x * x for x in v))
        if norm == 0:
            return v
        return [x / norm for x in v]

    def encode(self, text: str) -> list[float]:
        if not text:
            return [0.0] * 384
        model = self._get_model()
        if not model:
            return [0.0] * 384
        try:
            embeddings = list(model.embed([text]))
            if embeddings:
                return self.normalize_vector(embeddings[0].tolist())
        except Exception as e:  # noqa: BLE001
            _logger.error("Error during embedding encoding: %s", e)
        return [0.0] * 384

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        if not model:
            return [[0.0] * 384 for _ in texts]
        try:
            embeddings = list(model.embed(texts))
            return [self.normalize_vector(emb.tolist()) for emb in embeddings]
        except Exception as e:  # noqa: BLE001
            _logger.error("Error during batch embedding encoding: %s", e)
            return [[0.0] * 384 for _ in texts]

    def cron_generate_missing_embeddings(self, env):
        """
        Bulk generate embeddings for tasks that do not have one yet in a time-limited loop.
        Processes tasks in batches of 1000 and commits after each batch to prevent locks.
        Stops after 180 seconds (3 minutes) to avoid worker timeouts.
        """
        max_duration = 180  # Stop after 3 minutes
        start_time = time.time()
        batch_size = 1000

        while time.time() - start_time < max_duration:
            env.cr.execute("""
                SELECT t.id
                FROM project_task t
                LEFT JOIN project_task_embedding e ON e.task_id = t.id
                WHERE e.id IS NULL AND (t.name IS NOT NULL AND t.name != '')
                ORDER BY t.id ASC
                LIMIT %s
            """, (batch_size,))
            task_ids = [row[0] for row in env.cr.fetchall()]
            if not task_ids:
                break

            tasks = env['project.task'].sudo().browse(task_ids)
            texts = []
            task_data = []

            for task in tasks:
                name = task.name or ""
                description_html = task.description or ""
                description_text = html_to_inner_content(description_html) if description_html else ""
                content = f"{name} {description_text}".strip()
                content_hash = str(zlib.crc32(content.encode('utf-8')))
                texts.append(content)
                task_data.append((task.id, content_hash))

            if not texts:
                break

            vectors = self.encode_batch(texts)

            # Batch upsert via SQL
            for (task_id, content_hash), vector in zip(task_data, vectors):
                if not vector or all(math.isclose(v, 0.0, abs_tol=1e-9) for v in vector):
                    continue
                vector_str = f"[{','.join(map(str, vector))}]"
                env.cr.execute("""
                    INSERT INTO project_task_embedding (task_id, embedding, content_hash, embedding_dim, last_indexed)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (task_id) DO UPDATE
                    SET embedding = EXCLUDED.embedding,
                        content_hash = EXCLUDED.content_hash,
                        last_indexed = EXCLUDED.last_indexed
                """, (task_id, vector_str, content_hash, 384, fields.Datetime.now()))

            env.cr.commit()
