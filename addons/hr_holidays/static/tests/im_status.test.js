import { describe, test } from "@odoo/hoot";

import { Store } from "@mail/core/common/store_service";
import { startServer, start, openDiscuss, contains } from "@mail/../tests/mail_test_helpers";

import { serverState, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";

describe.current.tags("desktop");
defineHrHolidaysModels();

test("change icon on change partner im_status for leave variants", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].write([serverState.partnerId], { im_status: "online" });
    pyEnv["res.users"].write([serverState.userId], { leave_date_to: "2023-01-01" });
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    patchWithCleanup(Store, { IM_STATUS_DEBOUNCE_DELAY: 0 });
    await start();
    await openDiscuss(channelId);
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus .fa-plane[title='On Leave (Online)']"
    );
    pyEnv["bus.bus"]._sendone("broadcast", "bus.bus/im_status_updated", {
        partner_id: serverState.partnerId,
        im_status: "leave_offline",
        presence_status: "offline",
    });
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus .fa-plane[title='On Leave']");
    pyEnv["bus.bus"]._sendone("broadcast", "bus.bus/im_status_updated", {
        partner_id: serverState.partnerId,
        im_status: "leave_away",
        presence_status: "away",
    });
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus .fa-plane[title='On Leave (Idle)']"
    );
    pyEnv["bus.bus"]._sendone("broadcast", "bus.bus/im_status_updated", {
        partner_id: serverState.partnerId,
        im_status: "leave_online",
        presence_status: "online",
    });
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus .fa-plane[title='On Leave (Online)']"
    );
});
