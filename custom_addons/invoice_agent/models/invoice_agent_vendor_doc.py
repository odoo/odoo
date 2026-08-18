"""Vendor/GL history RAG corpus — pgvector-backed document store.

v0.10 — one ``invoice.agent.vendor.doc`` row per **posted** vendor bill,
carrying a 1024-dim ``voyage-3`` embedding. Odoo's ORM has no vector field
type, so the ``embedding`` column is added via raw SQL in ``init()`` — that
is the pattern this model documents:

* ``init(cr)`` runs ``ALTER TABLE ... ADD COLUMN IF NOT EXISTS embedding
  vector(1024)`` — idempotent, safe on every module upgrade.
* The HNSW index uses ``vector_cosine_ops`` (IVFFlat is faster to build but
  needs the right ``lists`` count tuned to data size; HNSW has no training
  step and stays fast as the corpus grows — the right choice for a few
  thousand bills that only ever grows).
* ``content`` is the compact RAG text rendered by
  ``account.move._build_rag_document()``; ``move_id`` and ``partner_id``
  let a cosine hit jump straight back to the bill.

Queries (run by the future RAG tool, or by hand for the EXPLAIN exercise):

```sql
SELECT partner_id, move_id, content,
       1 - (embedding <=> :query_vector) AS cosine_similarity
FROM invoice_agent_vendor_doc
ORDER BY embedding <=> :query_vector
LIMIT 10;
```

The HNSW index answers that ``ORDER BY ... <=>`` in O(log n) instead of a
full scan (verified by ``EXPLAIN ANALYZE`` in docs/vector-search.md).
"""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Must match the service's voyage-3 dimension (app/embeddings.py).
EMBEDDING_DIMENSIONS = 1024


class InvoiceAgentVendorDoc(models.Model):
    _name = "invoice.agent.vendor.doc"
    _description = "Vendor/GL history RAG document (pgvector embedding)"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        index=True,
        ondelete="cascade",
        help="Vendor the bill belongs to (denormalized for filtered search).",
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Posted Bill",
        index=True,
        ondelete="cascade",
        help="The posted vendor bill this document was rendered from. One "
        "document per posted bill — lines travel together with their GL "
        "codes (see account.move._build_rag_document).",
    )
    content = fields.Text(
        string="RAG Content",
        readonly=True,
        help="Compact text rendered by _build_rag_document(): partner name, "
        "invoice date, reference, then each line's name, GL code, quantity "
        "and subtotal.",
    )
    indexed_at = fields.Datetime(
        string="Indexed At",
        readonly=True,
        help="When the embedding was written (backfill or live post).",
    )
    # The vector(1024) column lives OUTSIDE the ORM (raw SQL init): Odoo has
    # no vector field type, and exposing it as a Json/Char would break the
    # pgvector operators. Searches go through raw SQL, never the ORM.

    _sql_constraints = [
        (
            "move_id_unique",
            "UNIQUE(move_id)",
            (
                "One RAG document per posted bill — a redelivered embed job "
                "upserts, never duplicates."
            ),
        ),
    ]

    # ------------------------------------------------------------------
    # schema bootstrap (raw SQL — ORM has no vector type)
    # ------------------------------------------------------------------
    def init(self):
        """Add the ``vector(1024)`` column + HNSW index idempotently."""
        super().init()
        # Self-contained extension bootstrap: the compose db image preloads
        # the pgvector binaries and its initdb hook enables the extension on
        # fresh volumes, but the CI runner's service container has no initdb
        # hook — so the addon creates it itself. `IF NOT EXISTS` keeps it a
        # no-op where the init script already ran. The db user is the
        # superuser in both compose (POSTGRES_USER=odoo) and CI.
        self.env.cr.execute("CREATE EXTENSION IF NOT EXISTS vector")
        self.env.cr.execute(
            """
            ALTER TABLE invoice_agent_vendor_doc
            ADD COLUMN IF NOT EXISTS embedding vector(%(dim)s)
            """,
            {"dim": EMBEDDING_DIMENSIONS},
        )
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS
            invoice_agent_vendor_doc_embedding_hnsw_idx
            ON invoice_agent_vendor_doc
            USING hnsw (embedding vector_cosine_ops)
            """
        )
        _logger.info(
            "invoice_agent_vendor_doc: vector(%d) column + HNSW cosine index",
            EMBEDDING_DIMENSIONS,
        )

    # ------------------------------------------------------------------
    # upsert / search (raw SQL against the vector column)
    # ------------------------------------------------------------------
    @api.model
    def upsert_embedding(self, move_id, content, vector_values):
        """Insert or replace the document for ``move_id`` with its embedding.

        :param vector_values: list of 1024 floats from the voyage-3 embedder.
        """
        move = self.env["account.move"].browse(move_id).exists()
        partner_id = move.partner_id.id if move else False
        vector_literal = "[" + ",".join(repr(float(v)) for v in vector_values) + "]"
        self.env.cr.execute(
            """
            INSERT INTO invoice_agent_vendor_doc
                (partner_id, move_id, content, embedding, indexed_at)
            VALUES (
                %(partner)s, %(move)s, %(content)s,
                %(vector)s::vector, now()
            )
            ON CONFLICT (move_id) DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                indexed_at = now()
            """,
            {
                "partner": partner_id,
                "move": int(move_id),
                "content": content or "",
                "vector": vector_literal,
            },
        )
        return True

    @api.model
    def search_similar(self, query_vector, limit=10):
        """Cosine-similarity search over the HNSW index (raw SQL)."""
        vector_literal = "[" + ",".join(repr(float(v)) for v in query_vector) + "]"
        self.env.cr.execute(
            """
            SELECT move_id, content,
                   1 - (embedding <=> %(v)s::vector) AS similarity
            FROM invoice_agent_vendor_doc
            ORDER BY embedding <=> %(v)s::vector
            LIMIT %(limit)s
            """,
            {"v": vector_literal, "limit": limit},
        )
        rows = self.env.cr.fetchall()
        if not rows:
            return self.env["account.move"]
        return self.env["account.move"].browse([row[0] for row in rows])
