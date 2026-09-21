from odoo.db.schema import column_exists

COLUMNS = (
    "social_twitter",
    "social_facebook",
    "social_github",
    "social_linkedin",
    "social_youtube",
    "social_instagram",
    "social_tiktok",
    "social_discord",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
