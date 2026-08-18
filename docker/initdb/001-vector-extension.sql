-- =============================================================================
-- pgvector bootstrap for the invoice_agent Postgres database.
--
-- Runs once on a fresh volume via the official docker-entrypoint-initdb.d
-- hook (mounted in docker-compose.yml). On an existing volume this file is a
-- no-op (the init scripts only execute when the data directory is empty).
--
-- Why an init script and not an Odoo migration for the extension itself:
-- `CREATE EXTENSION vector` must exist before ANY table (including Odoo's
-- base schema) can declare a vector column, and the Odoo image has no
-- guarantee of superuser rights on every deployment. The pgvector image
-- ships the extension binaries; this script just installs it + proves the
-- operators work (the milestone's manual-rank exercise).
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- -----------------------------------------------------------------------------
-- Milestone exercise: demo table with three hand-written 1024-dimensional
-- vectors, ranked by cosine distance (<=>) to show ordering matches
-- intuition. Same dimension as the real vendor-doc embeddings (voyage-3),
-- so the operator exercise exercises the production operator path.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS demo (
    id      serial PRIMARY KEY,
    label   text NOT NULL,
    embedding vector(1024)
);

-- The three vectors are built with core PostgreSQL array functions (no
-- extra dependencies): alpha points along axis 1, beta along axis 2
-- (orthogonal to alpha), gamma points along axis 1 at double magnitude
-- (same direction as alpha).
INSERT INTO demo (label, embedding) VALUES
    (
        'alpha',
        ('[' || array_to_string(ARRAY[1.0] || array_fill(0.0, ARRAY[1023]), ',') || ']')::vector
    ),
    (
        'beta',
        ('[' || array_to_string(array_fill(0.0, ARRAY[1]) || ARRAY[1.0] || array_fill(0.0, ARRAY[1022]), ',') || ']')::vector
    ),
    (
        'gamma',
        ('[' || array_to_string(ARRAY[2.0] || array_fill(0.0, ARRAY[1023]), ',') || ']')::vector
    )
ON CONFLICT DO NOTHING;

-- Sanity: gamma (same direction as alpha, twice the magnitude) must rank
-- FIRST against the alpha query — cosine is scale-invariant, so the L2
-- distance would be larger but cosine similarity is identical.
--   ORDER BY embedding <=>
--     ('[' || array_to_string(ARRAY[1.0] || array_fill(0.0, ARRAY[1023]), ',') || ']')::vector
--   => gamma (0), alpha (0), beta (~1.41)
-- (This query is re-runnable by hand via psql; the result row order is the
-- acceptance check.)

-- Operators shipped by the extension: <=> cosine distance, <-> L2 distance,
-- <#> negative inner product. HNSW indexes are declared with
-- vector_cosine_ops -> (see the invoice_agent_vendor_doc model init).
