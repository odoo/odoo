# Compare _get_related_posts() before/after the HEAD commit
# (website_forum: speed up similarity query).
#
# Run in an odoo shell where `env` is available, e.g.:
#   odoo shell -d <db> < compare_related_posts.py
# or paste it into an interactive `odoo shell` session.
#
# It runs BOTH the old and the new Jaccard-similarity SQL against the real
# data for a random sample of tagged posts and compares the *final output*
# (ordered id list, LIMIT applied) of the method. No code change is needed:
# both queries are embedded here.

from odoo.tools import SQL

SAMPLE_SIZE = 200
LIMIT = 5  # must match the default of _get_related_posts(limit=5)

# --- old query (HEAD~1) -----------------------------------------------------
OLD_SQL = """
    SELECT forum_post.id,
      -- Jaccard similarity
           (COUNT(DISTINCT intersection_tag_rel.forum_tag_id))::DECIMAL
           / COUNT(DISTINCT union_tag_rel.forum_tag_id)::DECIMAL AS similarity
      FROM forum_post
      -- common tags (intersection)
      JOIN forum_tag_rel AS intersection_tag_rel
        ON intersection_tag_rel.forum_post_id = forum_post.id
       AND intersection_tag_rel.forum_tag_id = ANY(%(tag_ids)s)
      -- union tags
RIGHT JOIN forum_tag_rel AS union_tag_rel
        ON union_tag_rel.forum_post_id = forum_post.id
        OR union_tag_rel.forum_post_id = %(current_post_id)s
     WHERE id != %(current_post_id)s
  GROUP BY forum_post.id
  ORDER BY similarity DESC,
           forum_post.last_activity_date DESC
     LIMIT %(limit)s
"""

# --- new query (HEAD) -------------------------------------------------------
NEW_SQL = """
    WITH candidates AS (
        SELECT forum_post_id, COUNT(forum_tag_id) AS intersection_count
          FROM forum_tag_rel
         WHERE forum_tag_id = ANY(%(tag_ids)s)
           AND forum_post_id != %(current_post_id)s
      GROUP BY forum_post_id
    )
    SELECT p.id,
        (c.intersection_count::DECIMAL /
        (
            cardinality(%(tag_ids)s) +
            (SELECT COUNT(*) FROM forum_tag_rel WHERE forum_post_id = p.id)
            - c.intersection_count
        )::DECIMAL) AS similarity
    FROM candidates c
    JOIN forum_post p
      ON p.id = c.forum_post_id
ORDER BY similarity DESC, p.last_activity_date DESC
   LIMIT %(limit)s
"""


def run(query, post):
    env.cr.execute(SQL(query, current_post_id=post.id, tag_ids=post.tag_ids.ids, limit=LIMIT))
    return env.cr.dictfetchall()


def sim_map(query, post):
    """Full {id: similarity} map, ignoring LIMIT/ORDER, to verify the math."""
    no_limit = query.replace("LIMIT %(limit)s", "")
    env.cr.execute(SQL(no_limit, current_post_id=post.id, tag_ids=post.tag_ids.ids, limit=LIMIT))
    return {r["id"]: r["similarity"] for r in env.cr.dictfetchall()}


# Random sample of tagged posts.
env.cr.execute(SQL(
    """
    SELECT forum_post_id
      FROM forum_tag_rel
  GROUP BY forum_post_id
     ORDER BY random()
     LIMIT %(n)s
    """,
    n=SAMPLE_SIZE,
))
post_ids = [r[0] for r in env.cr.fetchall()]
posts = env['forum.post'].browse(post_ids).exists()

mismatches = []
math_diffs = []  # posts where the similarity computation itself differs (real bug)
for post in posts:
    if not post.tag_ids:
        continue

    # Decisive correctness check: full similarity map, no LIMIT / no tie ordering.
    if sim_map(OLD_SQL, post) != sim_map(NEW_SQL, post):
        math_diffs.append(post.id)

    old = run(OLD_SQL, post)
    new = run(NEW_SQL, post)

    old_ids = [r["id"] for r in old]
    new_ids = [r["id"] for r in new]

    if old_ids != new_ids:
        # Distinguish a true difference from a harmless tie reordering:
        # equal as a set + identical similarity values => only ordering of
        # equal-similarity rows changed.
        old_map = {r["id"]: r["similarity"] for r in old}
        new_map = {r["id"]: r["similarity"] for r in new}
        same_set = set(old_ids) == set(new_ids)
        same_sims = all(
            old_map.get(i) == new_map.get(i) for i in set(old_ids) | set(new_ids)
        )
        mismatches.append({
            "post_id": post.id,
            "n_tags": len(post.tag_ids),
            "old": old,
            "new": new,
            "same_set": same_set,
            "same_similarities": same_sims,
            "tie_reorder_only": same_set and same_sims,
        })

print("=" * 70)
print(f"Compared {len(posts)} sampled tagged posts (LIMIT={LIMIT}).")
print(f"Similarity-math differences (no LIMIT, real bug if >0): {len(math_diffs)}")
if math_diffs:
    print(f"  affected post ids: {math_diffs}")
print(f"Mismatching ordered id lists: {len(mismatches)}")

real = [m for m in mismatches if not m["tie_reorder_only"]]
ties = [m for m in mismatches if m["tie_reorder_only"]]
print(f"  - tie-reorder only (same ids & similarities): {len(ties)}")
print(f"  - REAL differences: {len(real)}")
print("=" * 70)

for m in real:
    print(f"\nPOST {m['post_id']} ({m['n_tags']} tags)  "
          f"same_set={m['same_set']} same_similarities={m['same_similarities']}")
    print(f"  old: {[(r['id'], str(r['similarity'])) for r in m['old']]}")
    print(f"  new: {[(r['id'], str(r['similarity'])) for r in m['new']]}")

if not real:
    print("\nOK: no real differences — only (harmless) tie reorderings, if any.")
