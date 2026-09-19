{
    "name": "Partner Relationships",
    "version": "19.0.1.0.1",
    "category": "Sales/CRM",
    "summary": "Family, ritual and commercial ties between contacts, drawn as a network",
    "description": """
Partner Relationships
=====================

Several AgroMarin customers are related to each other -- by blood, by marriage,
by *compadrazgo*, or by farming the same land. That is commercially material and
was recorded nowhere.

**The model.** ``res.partner.relation`` is one row per tie, between two contacts,
typed by ``res.partner.relation.type``. A type declares which of three algebras it
follows, because they behave differently and collapsing them loses information:

* *symmetric* -- ``sibling of``, ``cousin of``, ``compadre of``,
  ``business partner of``, ``grows crop together with``. One row is the whole
  fact; a mirrored row is rejected, since it would draw two edges and double
  every degree count.
* *asymmetric* -- ``parent of`` / ``child of``, ``guarantor of`` /
  ``guaranteed by``. Stored once, read from either end.
* *gendered* -- ``father of`` and ``mother of`` are the same type read against a
  contact's ``gender``, as are ``compadre`` and ``comadre``.

A type also carries a ``category`` (consanguinity, affinity, ritual kinship,
household, business, agricultural), a civil-law ``degree``, and a ``weight_risk``
saying how strongly the tie implies a shared economic interest. ``compadre`` is
the reason ``category`` and ``degree`` are separate axes: ritual kinship carries
real economic obligation at zero genealogical distance.

**The analysis.** ``res.partner`` gains a breadth-first walk over that graph --
``_get_related_partners()`` for the related-party group and
``_get_relation_path()`` for the shortest chain between two contacts, worded from
each contact's own end ("Juan -- husband of -> Maria -- compadre of -> Pedro").
Both are batched one query per degree, not one per record.
""",
    "author": "AgroMarin",
    "website": "https://agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "partner",
        "web",
    ],
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "data/res_partner_relation_type_data.xml",
        "views/res_partner_relation_type_views.xml",
        "views/res_partner_relation_views.xml",
        "views/res_partner_views.xml",
        "wizards/partner_relation_path_views.xml",
        "views/ir_ui_menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "partner_relationship/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "partner_relationship/static/tests/**/*.js",
            (
                "remove",
                "partner_relationship/static/tests/tours/**/*.js",
            ),
        ],
        "web.assets_tests": [
            "partner_relationship/static/tests/tours/**/*.js",
        ],
    },
}
