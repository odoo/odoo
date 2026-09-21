{
    "name": "Partner Scoring / CRM",
    "version": "19.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "The customer's commercial tier on the lead, as a predictive-scoring feature",
    "description": """
A lead carries the commercial tier of the customer it names, so the pipeline
groups by it and predictive lead scoring can learn from it. No lead scoring is
added or moved: the tier is one more field the Bayesian model may read.
    """,
    "author": "AgroMarin",
    "website": "https://agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "partner_scoring",
        "crm",
    ],
    "data": [
        "data/crm_lead_scoring_frequency_field_data.xml",
        "views/crm_lead_views.xml",
    ],
    "auto_install": True,
}
