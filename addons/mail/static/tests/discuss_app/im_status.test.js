import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { Store } from "@mail/core/common/store_service";
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
    patchWithCleanup(Store, { IM_STATUS_DEBOUNCE_DELAY: 0 });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    pyEnv["res.users"].write([serverState.userId], { im_status: "online" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus[title='User is online']");
    pyEnv["res.users"].write([serverState.userId], { im_status: "offline" });
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        user_id: serverState.userId,
        im_status: "offline",
        presence_status: "offline",
    });
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus[title='User is offline']");
    pyEnv["res.users"].write([serverState.userId], { im_status: "away" });
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        user_id: serverState.userId,
        im_status: "away",
        presence_status: "away",
    });
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus[title='User is idle']");
    pyEnv["res.users"].write([serverState.userId], { im_status: "online" });
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        user_id: serverState.userId,
        im_status: "online",
        presence_status: "online",
    });
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
    await contains(".o-mail-NotificationItem:text('Demo')", {
        contains: ["i[aria-label='User is online']"],
    });
});
