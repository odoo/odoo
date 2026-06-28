import { describe, test } from "@odoo/hoot";

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
    const pyEnv = await startServer();
    pyEnv["hr.employee"].create({ user_id: serverState.userId, leave_date_to: "2023-01-01" });
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    patchWithCleanup(ImStatusMixin, { IM_STATUS_DEBOUNCE_DELAY: 0 });
    await start();
    await openDiscuss(channelId);
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus.fa-plane[title='User is on leave and online']"
    );
    sendPresenceUpdate("res.users", serverState.userId, "offline");
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus.fa-plane[title='User is on leave']"
    );
    sendPresenceUpdate("res.users", serverState.userId, "away");
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus.fa-plane[title='User is on leave and idle']"
    );
    sendPresenceUpdate("res.users", serverState.userId, "online");
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus.fa-plane[title='User is on leave and online']"
    );
});
