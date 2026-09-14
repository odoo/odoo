import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Keep telling every member of a security group that already asked them.

    19.0.2.2.0 treats a security group as a queue: members decide from To Review
    and nobody gets a personal activity. Existing group categories keep asking
    each member until someone turns it off on the category.
    """
    # 19.0.2.8.0 took the field off the model, so a database jumping here from
    # below 2.2 loads without the column. Create it: the 2.8 end-migration
    # reads it to decide whether the group step keeps asking its members,
    # which is exactly the choice this migration makes for them.
    cr.execute(
        "ALTER TABLE approval_category "
        "ADD COLUMN IF NOT EXISTS notify_pool_members boolean"
    )
    cr.execute(
        "UPDATE approval_category SET notify_pool_members = TRUE "
        "WHERE group_approval = 'exclusive'"
    )
    _logger.info(
        "approval 19.0.2.2.0: %d group categor(ies) keep notifying every member.",
        cr.rowcount,
    )
