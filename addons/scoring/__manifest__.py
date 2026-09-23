{
    "name": "Scoring",
    "version": "19.0.1.0.0",
    "category": "Hidden/Tools",
    "summary": "Scorecards: score a subject on dimensions, classify it into a band",
    "description": """
The scoring engine every scored model stands on.

A ``scorecard`` scores the records of one model (its *subjects*) on
``scorecard.dimension`` records. A dimension turns an observation into points
against a ceiling: a *catalog* dimension reads values the subject holds that
carry their own weight (an attribute value, a crop), the ceiling being the
catalog's; a *measure* dimension reads a number the subject yields and bands it
through ``scorecard.dimension.band`` records, the ceiling being the dimension's
weight. Every point is an audit row (``mixin.score.line``), the normalized total
is ``score`` on the subject (``mixin.scored``), and a scale of bands
(``mixin.score.scale``) classifies it. The engine only evaluates: which
dimensions exist, what they weigh and where the bands lie is data.

A host declares ``_inherit = "mixin.scored"`` with ``_score_line_model`` naming
its concrete audit line, ships a scorecard record, and answers each dimension's
code with ``_score_observe_<code>`` (the observation), optionally
``_score_ceiling_<code>``, ``_score_bands_<code>``, ``_score_rows_<code>`` and
``_score_labels_<code>``. ``partner_scoring`` is the first host; its
``agro_partner_scoring`` specialization adds three dimensions as data.

Refresh is incremental and queued: rows are reconciled by identity, waves go
through ``ir.job`` with a deduplicating identity key, and a catalog, scale,
dimension or band edit notifies the subjects it governs.
    """,
    "author": "AgroMarin",
    "website": "https://agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "base",
    ],
    "data": [
        "security/res_groups_security.xml",
        "security/ir.access.csv",
        "data/ir_job_channel_data.xml",
        "views/scorecard_views.xml",
        "views/scoring_menus.xml",
    ],
}
