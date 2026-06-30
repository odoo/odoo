import { onRpc } from "@web/../tests/web_test_helpers";

onRpc("/bus/has_missed_notifications", function hasMissedNotifications() {
    return false;
});
