/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Persona } from "@mail/core/common/persona_model";
import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("im status");

QUnit.test("initially online", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Online']");
});

QUnit.test("initially offline", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "offline" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Offline']");
});

QUnit.test("initially away", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "away" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Idle']");
});

QUnit.test("change icon on change partner im_status", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].write([pyEnv.currentPartnerId], { im_status: "online" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: pyEnv.currentPartnerId })],
        channel_type: "chat",
    });
    patchWithCleanup(Persona, { IM_STATUS_DEBOUNCE_DELAY: 0 });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Online']");

    pyEnv["res.partner"].write([pyEnv.currentPartnerId], { im_status: "offline" });
    pyEnv["bus.bus"]._sendone("broadcast", "bus.bus/im_status_updated", {
        partner_id: pyEnv.currentPartnerId,
        im_status: "offline",
        presence_status: "offline",
    });
    await contains(".o-mail-ImStatus i[title='Offline']");

    pyEnv["res.partner"].write([pyEnv.currentPartnerId], { im_status: "away" });
    pyEnv["bus.bus"]._sendone("broadcast", "bus.bus/im_status_updated", {
        partner_id: pyEnv.currentPartnerId,
        im_status: "away",
        presence_status: "away",
    });
    await contains(".o-mail-ImStatus i[title='Idle']");

    pyEnv["res.partner"].write([pyEnv.currentPartnerId], { im_status: "online" });
    pyEnv["bus.bus"]._sendone("broadcast", "bus.bus/im_status_updated", {
        partner_id: pyEnv.currentPartnerId,
        im_status: "online",
        presence_status: "online",
    });
    await contains(".o-mail-ImStatus i[title='Online']");
});

QUnit.test("show im status in messaging menu preview of chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
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
