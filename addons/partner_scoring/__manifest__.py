{
    "name": "Partner Scoring",
    "version": "19.0.1.10.0",
    "category": "Sales/CRM",
    "summary": "Weighted attribute scoring for customers, with commercial tiers",
    "description": """
Configurable customer scoring engine on ``res.partner``.

Partners are described by an EAV taxonomy (``res.partner.attribute`` and its
values), each value can carry a weight, and every attribute says how its values
combine (sum, highest, or not scored). The weighted total is normalized against
the catalog ceiling into a 0-100 percentage, which classifies the partner into a
``partner.tier`` — a half-open score band carrying a commercial ``factor``
applied downstream to revenue targets.

The shipped catalog is a taxonomy, not a working scale: of the 15 seeded
attributes only ``Commercial profile``, ``Loyalty``, ``Technology level`` and
``Growth outlook`` carry weight -- the four that were being captured when the
scale was calibrated -- so out of the box those four are the only ones that
move the score and appear in the breakdown. A weighted attribute nobody
captures scores everyone zero over a larger ceiling, so weight the rest only as
they start being captured.

Every point is explained: ``partner.score.line`` holds one audit row per source,
including the ones that scored zero and the ones an aggregation mode discarded.

The engine is ``scoring``: ``res.partner`` is a ``mixin.scored`` host, the
``partner_scoring.scorecard_partner`` scorecard carries one catalog dimension,
``partner_attr``, and ``partner.tier`` is the ``mixin.score.scale`` that
classifies the score. A module adds a dimension as a record on that scorecard
plus the host hooks its code names (``_score_observe_<code>``, and
``_score_rows_<code>`` when the rows need a shape of their own); see
``agro_partner_scoring``, which scores partners on their crops, cultivated area
and surface attributes.

This is deliberately not a ``crm_*`` module: it never touches ``crm.lead``. It
scores the customer, not the opportunity, and is unrelated to Odoo's predictive
lead scoring (``crm.lead.scoring.frequency``).
    """,
    "author": "AgroMarin",
    "website": "https://agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "mixin_attribute",
        "partner",
        "scoring",
    ],
    "data": [
        "security/res_groups_security.xml",
        "security/ir.access.csv",
        "data/ir_actions_server_data.xml",
        "data/scorecard_data.xml",
        "data/res_partner_attribute_data.xml",
        "data/res_partner_attribute_value_data.xml",
        "views/res_partner_attribute_views.xml",
        "views/partner_tier_views.xml",
        "views/partner_score_line_views.xml",
        "views/res_partner_views.xml",
        "views/res_partner_search_views.xml",
        "views/scorecard_views.xml",
        "views/partner_scoring_menus.xml",
    ],
}
