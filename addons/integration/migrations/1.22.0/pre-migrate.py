import logging

_logger = logging.getLogger(__name__)

FROM_MODULE = "api_gateway"
TO_MODULE = "integration"

CRON_ACTION_SUFFIX = "_ir_actions_server"

_STALE_CRONS = (
    "cron_health_check_services",
    "cron_reset_cache_errors",
    "cron_check_expiring_credentials",
)

_GROUP_MERGES = (
    ("group_api_gateway_user", "group_api_transport_user"),
    ("group_api_gateway_admin", "group_api_transport_admin"),
)

_PARAM_MOVES = (
    ("api_gateway.log_retention_days", "integration.log_retention_days"),
    ("api_gateway.max_cache_entries", "integration.max_cache_entries"),
)

_PARAM_DROPS = (
    "api_gateway.enable_global_logging",
    "api_gateway.redact_sensitive",
    "api_gateway.session_cache_size",
    "api_gateway.session_cache_ttl",
)


def _drop_reflection_debris(cr):
    """Delete api_gateway xmlids for records another module already owns.

    These are the `ir.model`, `ir.model.fields` and selection rows the registry
    reflects once per module that touches a model. The record belongs to whoever
    still declares it, so this deletes stale pointers and no records at all.
    """
    cr.execute(
        """
        DELETE FROM ir_model_data gw
         WHERE gw.module = %s
           AND EXISTS (
               SELECT 1 FROM ir_model_data owner
                WHERE owner.model = gw.model
                  AND owner.res_id = gw.res_id
                  AND owner.module <> gw.module
           )
        """,
        (FROM_MODULE,),
    )
    return cr.rowcount


def _drop_stale_crons(cr):
    """Remove the three crons integration replaced, companion included.

    A cron loaded from XML owns two xmlids: itself and the `ir.actions.server`
    it delegates to. 1.6.0 deleted only the first, which is why two server
    actions here outlived their crons. The action has to go after the cron --
    the foreign key from `ir_cron` is RESTRICT.
    """
    companions = [name + CRON_ACTION_SUFFIX for name in _STALE_CRONS]
    cr.execute(
        """
        DELETE FROM ir_cron
         WHERE id IN (SELECT res_id FROM ir_model_data
                       WHERE module = %s AND model = 'ir.cron' AND name = ANY(%s))
        """,
        (FROM_MODULE, list(_STALE_CRONS)),
    )
    crons = cr.rowcount
    cr.execute(
        """
        DELETE FROM ir_act_server
         WHERE id IN (SELECT res_id FROM ir_model_data
                       WHERE module = %s
                         AND model = 'ir.actions.server'
                         AND name = ANY(%s))
        """,
        (FROM_MODULE, companions),
    )
    actions = cr.rowcount
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = %s AND name = ANY(%s)",
        (FROM_MODULE, list(_STALE_CRONS) + companions),
    )
    return crons, actions


def _group_id(cr, name):
    """Find a group by xmlid name under either module.

    1.6.0 was meant to rehome these before 1.7.0 looked for them, so 1.7.0
    searched `integration` alone, found nothing and merged nothing. Accepting
    either owner is what makes this runnable however far the chain got.
    """
    cr.execute(
        """
        SELECT res_id FROM ir_model_data
         WHERE model = 'res.groups' AND name = %s AND module IN (%s, %s)
         ORDER BY module = %s DESC
         LIMIT 1
        """,
        (name, FROM_MODULE, TO_MODULE, TO_MODULE),
    )
    row = cr.fetchone()
    return row[0] if row else None


def _carry_grants(cr, old_id, new_id):
    """Move the old group's ACL and record-rule rows onto the new group.

    1.7.0 deleted them, on the assumption that the new group already grants
    whatever the old one did. For `integration.service` that holds; for
    `api.credential.wizard` it does not, and `group_api_gateway_admin` carries
    the only grant on it that is not `base.group_system`. Deleting a group's
    ACL rows narrows access whether or not its members moved -- a group confers
    nothing by itself, so membership arriving intact is not the same as access
    arriving intact.

    A row is dropped only where the new group already covers that model or rule,
    which is a genuine duplicate rather than a grant.
    """
    cr.execute(
        """
        DELETE FROM ir_model_access old
         WHERE old.group_id = %s
           AND EXISTS (SELECT 1 FROM ir_model_access new
                        WHERE new.group_id = %s AND new.model_id = old.model_id)
        """,
        (old_id, new_id),
    )
    cr.execute(
        "UPDATE ir_model_access SET group_id = %s WHERE group_id = %s",
        (new_id, old_id),
    )
    acls = cr.rowcount
    cr.execute(
        """
        DELETE FROM rule_group_rel old
         WHERE old.group_id = %s
           AND EXISTS (SELECT 1 FROM rule_group_rel new
                        WHERE new.group_id = %s
                          AND new.rule_group_id = old.rule_group_id)
        """,
        (old_id, new_id),
    )
    cr.execute(
        "UPDATE rule_group_rel SET group_id = %s WHERE group_id = %s",
        (new_id, old_id),
    )
    return acls, cr.rowcount


def _carry_implied_reach(cr, old_id, new_id):
    """Grant the old group's members, directly, whatever it implied that they
    will no longer reach once it is gone.

    Handing the new group the old one's implications is the tidy graph operation
    and the wrong one here: `group_api_gateway_admin` implies `base.group_system`,
    so the new group would confer Administrator on all of its members, including
    those who were never gateway admins. Granting the reach to the users who
    actually had it changes nobody else's rights.

    Runs after membership has been carried, so the new group counts as kept.
    """
    cr.execute(
        """
        WITH RECURSIVE old_reach(gid) AS (
            SELECT hid FROM res_groups_implied_rel WHERE gid = %(old)s
          UNION
            SELECT i.hid FROM res_groups_implied_rel i
              JOIN old_reach r ON i.gid = r.gid
        ), members AS (
            SELECT uid FROM res_groups_users_rel WHERE gid = %(old)s
        ), kept(uid, gid) AS (
            SELECT r.uid, r.gid FROM res_groups_users_rel r
              JOIN members m ON m.uid = r.uid
             WHERE r.gid <> %(old)s
          UNION
            SELECT k.uid, i.hid FROM kept k
              JOIN res_groups_implied_rel i ON i.gid = k.gid
        )
        INSERT INTO res_groups_users_rel (gid, uid)
        SELECT o.gid, m.uid
          FROM old_reach o CROSS JOIN members m
         WHERE o.gid <> %(old)s
           AND NOT EXISTS (
               SELECT 1 FROM kept k WHERE k.uid = m.uid AND k.gid = o.gid
           )
        ON CONFLICT DO NOTHING
        """,
        {"old": old_id, "new": new_id},
    )
    return cr.rowcount


def _merge_groups(cr):
    """Fold the gateway groups into the transport ones, preserving both halves.

    Membership and access are separate things and both have to survive: the
    members move, the ACL and rule rows move, and anything the old group reached
    by implication is granted to its own members. Only then is the group itself
    removed, so nobody passes through a state where they hold neither.
    """
    carried = acls = rules = reach = 0
    for old_name, new_name in _GROUP_MERGES:
        old_id = _group_id(cr, old_name)
        new_id = _group_id(cr, new_name)
        if not old_id or not new_id or old_id == new_id:
            continue

        cr.execute(
            """
            INSERT INTO res_groups_users_rel (gid, uid)
            SELECT %s, old.uid FROM res_groups_users_rel old WHERE old.gid = %s
            ON CONFLICT DO NOTHING
            """,
            (new_id, old_id),
        )
        carried += cr.rowcount

        reach += _carry_implied_reach(cr, old_id, new_id)
        moved_acls, moved_rules = _carry_grants(cr, old_id, new_id)
        acls += moved_acls
        rules += moved_rules

        cr.execute(
            "DELETE FROM res_groups_implied_rel WHERE gid = %s OR hid = %s",
            (old_id, old_id),
        )
        cr.execute("DELETE FROM res_groups_users_rel WHERE gid = %s", (old_id,))
        cr.execute("DELETE FROM res_groups WHERE id = %s", (old_id,))
        cr.execute(
            "DELETE FROM ir_model_data WHERE model = 'res.groups' AND name = %s",
            (old_name,),
        )
        _logger.info(
            "19.0.1.22.0: merged %s into %s -- members, ACL rows, record rules "
            "and implied reach all carried",
            old_name,
            new_name,
        )
    return carried, acls, rules, reach


def _drop_privilege(cr):
    cr.execute(
        """
        SELECT res_id FROM ir_model_data
         WHERE model = 'res.groups.privilege'
           AND name = 'res_groups_privilege_api_gateway'
           AND module IN (%s, %s)
        """,
        (FROM_MODULE, TO_MODULE),
    )
    row = cr.fetchone()
    if not row:
        return
    cr.execute("DELETE FROM res_groups_privilege WHERE id = %s", (row[0],))
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE model = 'res.groups.privilege'
           AND name = 'res_groups_privilege_api_gateway'
        """
    )
    _logger.info("19.0.1.22.0: dropped the API Gateway privilege")


def _move_parameters(cr):
    """Retire the gateway keys, and never overwrite a live destination.

    1.7.0 let the gateway value win the collision. By the time this runs the
    destination key has been the one actually read for months, so carrying a
    stale value onto it would be a regression rather than a migration.
    """
    moved = 0
    for old_key, new_key in _PARAM_MOVES:
        cr.execute(
            """
            INSERT INTO ir_config_parameter (key, value)
            SELECT %s, old.value FROM ir_config_parameter old WHERE old.key = %s
            ON CONFLICT (key) DO NOTHING
            """,
            (new_key, old_key),
        )
        moved += cr.rowcount
        cr.execute("DELETE FROM ir_config_parameter WHERE key = %s", (old_key,))
    cr.execute(
        "DELETE FROM ir_config_parameter WHERE key = ANY(%s)",
        (list(_PARAM_DROPS),),
    )
    return moved, cr.rowcount


def migrate(cr, version):
    """Re-run the api_gateway retirement that 1.6.0 and 1.7.0 both skipped.

    1.6.0 opened with `SELECT count(*) FROM ir_module_module WHERE name =
    'api_gateway'` and returned when it found none. On a database where that row
    had already been removed -- which is the state the retirement exists to
    produce -- the guard read "nothing to do" from the very evidence that the
    work was outstanding, so it adopted nothing. 1.7.0 then looked for the groups
    under `integration`, where 1.6.0 was supposed to have put them, found none
    and skipped every merge without a word.

    What is left is a module that exists only as `ir_model_data` rows: no
    `ir_module_module` row, so it never appears in `updated_modules` and its
    records are never swept, never updated and never removed. Two groups kept
    real members and their own ACL rows, and four settings stayed on keys with
    no reader.

    This keys off the leftover rows instead of the module row, which is what the
    guard should have asked about. It stops short of adopting what remains:
    integration does not declare those menus, views and actions, so adopting
    them would hand them to the next stale-data sweep to delete. They are named
    in the log for a deliberate decision instead.
    """
    cr.execute("SELECT count(*) FROM ir_model_data WHERE module = %s", (FROM_MODULE,))
    if not cr.fetchone()[0]:
        return

    debris = _drop_reflection_debris(cr)
    crons, actions = _drop_stale_crons(cr)
    carried, acls, rules, reach = _merge_groups(cr)
    _drop_privilege(cr)
    moved, dropped = _move_parameters(cr)

    cr.execute(
        """
        SELECT model, count(*) FROM ir_model_data
         WHERE module = %s GROUP BY model ORDER BY model
        """,
        (FROM_MODULE,),
    )
    remaining = cr.fetchall()

    _logger.info(
        "19.0.1.22.0: dropped %s reflection pointer(s), %s stale cron(s) and %s "
        "orphaned server action(s); carried %s membership(s), %s ACL row(s), %s "
        "record rule(s) and %s implied grant(s); moved %s setting(s) and deleted "
        "%s that had no reader.",
        debris,
        crons,
        actions,
        carried,
        acls,
        rules,
        reach,
        moved,
        dropped,
    )
    if remaining:
        _logger.warning(
            "19.0.1.22.0: %s still owns %s. integration does not declare them, "
            "so adopting them would hand them to the next stale-data sweep. "
            "Retire them deliberately or leave them where they are.",
            FROM_MODULE,
            ", ".join(f"{count} {model}" for model, count in remaining),
        )
