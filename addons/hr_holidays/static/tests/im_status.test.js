import { describe, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";

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

test("change icon on change partner im_status for leave variants", async () => {
    const pyEnv = await startServer();
    pyEnv["hr.employee"].create({ user_id: serverState.userId, leave_date_to: "2023-01-01" });
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    patchWithCleanup(ImStatusMixin, { IM_STATUS_DEBOUNCE_DELAY: 0 });
    await start();
    await openDiscuss(channelId);
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title='User is on leave and online']:count(1)"
    );
    sendPresenceUpdate("res.users", serverState.userId, "offline");
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title='User is on leave']:count(1)"
    );
    sendPresenceUpdate("res.users", serverState.userId, "away");
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title='User is on leave and idle']:count(1)"
    );
    sendPresenceUpdate("res.users", serverState.userId, "online");
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title='User is on leave and online']:count(1)"
    );
});
