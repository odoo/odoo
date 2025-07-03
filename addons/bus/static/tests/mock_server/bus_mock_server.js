import { onRpc } from "@web/../tests/web_test_helpers";
import { serializeDateTime } from "@web/core/l10n/dates";

onRpc("/bus/get_autovacuum_info", function getAutovacuumInfo() {
    return {
        lastcall: serializeDateTime(luxon.DateTime.now().minus({ days: 1 }).toUTC()),
        nextcall: serializeDateTime(luxon.DateTime.now().plus({ days: 1 }).toUTC()),
    };
});
onRpc("/bus/has_missed_notifications", function hasMissedNotifications() {
    return false;
});
