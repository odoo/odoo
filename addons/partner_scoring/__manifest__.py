{
    "name": "Partner Scoring",
    "version": "19.0.1.6.0",
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
attributes only ``Commercial profile``, ``Loyalty`` and ``Technology level``
carry any weight, so out of the box those three are the only ones that move the
score and the only ones that appear in the breakdown. Weighting the rest is the
operator's first configuration task.

Every point is explained: ``partner.score.line`` holds one audit row per source,
including the ones that scored zero and the ones an aggregation mode discarded.

The scoring pipeline is extensible. A module adds a dimension by extending
``res.partner._get_score_dimensions()`` and supplying ``_score_ceiling_<name>``
and ``_score_rows_<name>``; see ``agro_partner_scoring``, which scores partners
on their crops, cultivated area and surface attributes.

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
    ],
    "data": [
        "security/res_groups_security.xml",
        "security/ir.model.access.csv",
        "security/ir_rule_security.xml",
        "data/ir_actions_server_data.xml",
        "data/ir_job_channel_data.xml",
        "data/res_partner_attribute_data.xml",
        "data/res_partner_attribute_value_data.xml",
        "views/res_partner_attribute_views.xml",
        "views/partner_tier_views.xml",
        "views/partner_score_line_views.xml",
        "views/res_partner_views.xml",
        "views/partner_scoring_menus.xml",
    ],
}
