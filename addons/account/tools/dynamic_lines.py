from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


def filter_trivial(mapping):
    return {k: v for k, v in mapping.items() if "id" not in v}


def plan_dynamic_line_sync(
    existing_before,
    existing_after,
    needed_before,
    needed_after,
    values_differ,
):
    if needed_after == needed_before:
        _debug.logic("plan_dynamic_line_sync_needed_values_unchanged")
        return None
    if not needed_before and (
        filter_trivial(existing_after) != filter_trivial(existing_before)
    ):
        _debug.logic("plan_dynamic_line_sync_existing_lines_changed_hand")
        return None

    lines_by_after_key = {}
    for line, key in existing_after.items():
        lines_by_after_key.setdefault(key, []).append(line)

    to_delete = [
        line
        for line, key in existing_before.items()
        if key not in needed_after
        and key in lines_by_after_key
        and existing_after.get(line) not in needed_after
    ]
    to_delete_set = set(to_delete)
    to_delete.extend(
        line
        for line, key in existing_after.items()
        if key not in needed_after and line not in to_delete_set
    )
    to_delete_set = set(to_delete)

    to_create = {
        key: values
        for key, values in needed_after.items()
        if key not in lines_by_after_key
    }

    to_write = {}
    for key, values in needed_after.items():
        lines = lines_by_after_key.get(key)
        if not lines:
            continue
        keep_line, *extra_lines = lines
        for extra_line in extra_lines:
            if extra_line not in to_delete_set:
                to_delete.append(extra_line)
                to_delete_set.add(extra_line)
        if values_differ(keep_line, values):
            to_write[keep_line] = values

    return to_delete, to_create, to_write
