import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { Persona } from "@mail/core/common/persona_model";
import { describe, test } from "@odoo/hoot";
import { Command, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("initially online", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Online']");
});

test("initially offline", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "offline" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Offline']");
});

test("initially away", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "away" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Idle']");
});

test("change icon on change partner im_status", async () => {
    patchWithCleanup(Persona, { IM_STATUS_DEBOUNCE_DELAY: 0 });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "chat",
    });
    pyEnv["res.partner"].write([serverState.partnerId], { im_status: "online" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Online']");
    pyEnv["res.partner"].write([serverState.partnerId], { im_status: "offline" });
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        partner_id: serverState.partnerId,
        im_status: "offline",
    });
    await contains(".o-mail-ImStatus i[title='Offline']");
    pyEnv["res.partner"].write([serverState.partnerId], { im_status: "away" });
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        partner_id: serverState.partnerId,
        im_status: "away",
    });
    await contains(".o-mail-ImStatus i[title='Idle']");
    pyEnv["res.partner"].write([serverState.partnerId], { im_status: "online" });
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        partner_id: serverState.partnerId,
        im_status: "online",
    });
    await contains(".o-mail-ImStatus i[title='Online']");
});

test("show im status in messaging menu preview of chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", {
        text: "Demo",
        contains: ["i[aria-label='User is online']"],
    });
});
