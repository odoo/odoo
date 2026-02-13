import { describe, test } from "@odoo/hoot";

import { Store } from "@mail/core/common/store_service";
import { startServer, start, openDiscuss, contains } from "@mail/../tests/mail_test_helpers";

import { serverState, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";

describe.current.tags("desktop");
defineHrHolidaysModels();

test("change icon on change partner im_status for leave variants", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], { im_status: "online" });
    pyEnv["hr.employee"].create({ user_id: serverState.userId, leave_date_to: "2023-01-01" });
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    patchWithCleanup(Store, { IM_STATUS_DEBOUNCE_DELAY: 0 });
    await start();
    await openDiscuss(channelId);
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus.fa-plane[title='User is on leave and online']"
    );
    pyEnv["bus.bus"]._sendone("broadcast", "bus.bus/im_status_updated", {
        user_id: serverState.userId,
        im_status: "offline",
        presence_status: "offline",
    });
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus.fa-plane[title='User is on leave']"
    );
    pyEnv["bus.bus"]._sendone("broadcast", "bus.bus/im_status_updated", {
        user_id: serverState.userId,
        im_status: "away",
        presence_status: "away",
    });
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus.fa-plane[title='User is on leave and idle']"
    );
    pyEnv["bus.bus"]._sendone("broadcast", "bus.bus/im_status_updated", {
        user_id: serverState.userId,
        im_status: "online",
        presence_status: "online",
    });
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus.fa-plane[title='User is on leave and online']"
    );
});
