import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Split the challenge roster into its domain part and its manual part.

    ``gamification.challenge.user_ids`` used to be a plain many2many that
    ``_recompute_challenge_users`` only ever added to.  It is now a stored
    compute over ``user_domain``, ``manual_user_ids`` and the competing teams,
    which means the domain is authoritative and narrowing it narrows the
    challenge.

    Without this script the recompute would drop every hand-added participant on
    the first run, so the rows the old code cannot account for -- the ones the
    domain does *not* select -- are carried across into ``manual_user_ids``
    first.  Users the domain still matches need no row: the compute re-derives
    them, and copying them would freeze today's domain result for ever, which is
    the behaviour being removed.

    :param cr: database cursor
    :param version: module version being upgraded from
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        """
        SELECT gamification_challenge_id, ARRAY_AGG(res_users_id)
          FROM gamification_challenge_users_rel
      GROUP BY gamification_challenge_id
        """
    )
    existing = dict(cr.fetchall())
    if not existing:
        return

    Challenge = env["gamification.challenge"]
    carried = 0
    for challenge in Challenge.browse(existing).exists():
        roster = set(existing[challenge.id])
        derived = set()
        if challenge.user_domain:
            try:
                derived = set(
                    challenge._get_challenger_users(challenge.user_domain).ids
                )
            except Exception:
                # A domain that no longer parses (a field a module dropped) must
                # not abort the upgrade; treat it as selecting nobody, which
                # carries the whole roster over as manual and loses no member.
                _logger.warning(
                    "t-gam: challenge %s has an unusable user_domain %r; "
                    "carrying its whole roster over as manual participants",
                    challenge.id,
                    challenge.user_domain,
                    exc_info=True,
                )
        if challenge.challenge_mode == "team":
            derived |= set(challenge.team_ids.member_ids.ids)
        if manual := roster - derived:
            challenge.manual_user_ids = [(6, 0, sorted(manual))]
            carried += len(manual)

    env.flush_all()
    Challenge.search([]).invalidate_recordset(["user_ids"])
    _logger.info(
        "t-gam: carried %s hand-added participant(s) across %s challenge(s)",
        carried,
        len(existing),
    )
