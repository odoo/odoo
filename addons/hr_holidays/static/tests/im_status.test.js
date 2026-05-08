import { describe, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";

import {
    openDiscuss,
    sendPresenceUpdate,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { ImStatusMixin } from "@mail/core/common/im_status_mixin";

import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";
import { patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineHrHolidaysModels();

const { DateTime } = luxon;

test("change icon on change partner im_status for leave variants", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        leave_date_to: DateTime.now().plus({ days: 3 }).toISODate(),
    });
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    patchWithCleanup(ImStatusMixin, { IM_STATUS_DEBOUNCE_DELAY: 0 });
    await start();
    await openDiscuss(channelId);
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title^='User is on leave and online ·']:count(1)"
    );
    sendPresenceUpdate("res.users", serverState.userId, "offline");
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title^='User is on leave ·']:count(1)"
    );
    sendPresenceUpdate("res.users", serverState.userId, "away");
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title^='User is on leave and idle ·']:count(1)"
    );
    sendPresenceUpdate("res.users", serverState.userId, "online");
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title^='User is on leave and online ·']:count(1)"
    );
});
