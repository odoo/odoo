from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "gamification_achievement_unlock", ["rarity"])
    schema.drop_columns(cr, "gamification_activity", ["company_id"])
    schema.drop_columns(cr, "gamification_badge_user", ["level"])
    schema.drop_columns(cr, "gamification_goal", ["challenge_id"])
    schema.drop_columns(cr, "gamification_kudos", ["sender_partner_id", "recipient_partner_id"])
