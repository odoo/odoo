import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    sendPresenceUpdate,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { ImStatusMixin } from "@mail/core/common/im_status_mixin";
import { describe, test } from "@odoo/hoot";
import { Command, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("initially online", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId, im_status: "online" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus[title='User is online']");
});

test("initially offline", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId, im_status: "offline" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus[title='User is offline']");
});

test("initially away", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId, im_status: "away" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus[title='User is idle']");
});

test("change icon on change partner im_status", async () => {
    patchWithCleanup(ImStatusMixin, { IM_STATUS_DEBOUNCE_DELAY: 0 });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus[title='User is online']");
    sendPresenceUpdate("res.users", serverState.userId, "offline");
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus[title='User is offline']");
    sendPresenceUpdate("res.users", serverState.userId, "away");
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus[title='User is idle']");
    sendPresenceUpdate("res.users", serverState.userId, "online");
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus[title='User is online']");
});

test("show im status in messaging menu preview of chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId, im_status: "online" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem:has(.o-mail-NotificationItem-name:text('Demo'))", {
        contains: ["i[aria-label='User is online']"],
    });
});
