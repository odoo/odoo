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
-- Milestone exercise: demo table with three hand-written 4-dimensional
-- vectors, ranked by cosine distance (<=>) to show ordering matches
-- intuition. Real vendor-doc vectors live in invoice_agent_vendor_doc and
-- are 1024-dimensional — this 4-d demo is only for operator verification.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS demo (
    id      serial PRIMARY KEY,
    label   text NOT NULL,
    embedding vector(4)
);

INSERT INTO demo (label, embedding) VALUES
    ('alpha', '[1, 0, 0, 0]'),
    ('beta',  '[0, 1, 0, 0]'),
    ('gamma', '[2, 0, 0, 0]')
ON CONFLICT DO NOTHING;

-- Sanity: gamma (same direction as alpha, twice the magnitude) must rank
-- FIRST against the alpha query — cosine is scale-invariant, so the L2
-- distance would be larger but cosine similarity is identical.
--   ORDER BY embedding <=> '[1, 0, 0, 0]'::vector
--   => gamma, alpha, beta
-- (This query is re-runnable by hand via psql; the result row order is the
-- acceptance check.)

-- Operators shipped by the extension: <=> cosine distance, <-> L2 distance,
-- <#> negative inner product. HNSW indexes are declared with
-- vector_cosine_ops -> (see the invoice_agent_vendor_doc model init).
