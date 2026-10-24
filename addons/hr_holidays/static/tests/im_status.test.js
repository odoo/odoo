import { describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";

import {
    contains,
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

test("change icon on change partner im_status for leave variants", async () => {
    mockDate("2022-12-30 12:00:00");
    const pyEnv = await startServer();
    pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        leave_datetime_to: "2023-01-01 08:00:00",
    });
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    patchWithCleanup(ImStatusMixin, { IM_STATUS_DEBOUNCE_DELAY: 0 });
    await start();
    await openDiscuss(channelId);
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title='User is on leave and online']"
    );
    sendPresenceUpdate("res.users", serverState.userId, "offline");
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title='User is on leave']"
    );
    sendPresenceUpdate("res.users", serverState.userId, "away");
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title='User is on leave and idle']"
    );
    sendPresenceUpdate("res.users", serverState.userId, "online");
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title='User is on leave and online']"
    );
});
