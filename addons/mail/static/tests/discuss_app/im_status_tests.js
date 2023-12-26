/** @odoo-module **/

import { UPDATE_BUS_PRESENCE_DELAY } from "@bus/im_status_service";
import { start, startServer, click } from "@mail/../tests/helpers/test_utils";
import { Command } from "@mail/../tests/helpers/command";

import { createLocalId } from "@mail/utils/misc";
import { nextTick } from "@web/../tests/helpers/utils";
import { contains } from "@web/../tests/utils";

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
    await openDiscuss(channelId);
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
    await openDiscuss(channelId);
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
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Idle']");
});

QUnit.test("change icon on change partner im_status", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Online']");

    pyEnv["res.partner"].write([partnerId], { im_status: "offline" });
    await advanceTime(UPDATE_BUS_PRESENCE_DELAY);
    await contains(".o-mail-ImStatus i[title='Offline']");

    pyEnv["res.partner"].write([partnerId], { im_status: "away" });
    await advanceTime(UPDATE_BUS_PRESENCE_DELAY);
    await contains(".o-mail-ImStatus i[title='Idle']");

    pyEnv["res.partner"].write([partnerId], { im_status: "online" });
    await advanceTime(UPDATE_BUS_PRESENCE_DELAY);
    await contains(".o-mail-ImStatus i[title='Online']");
});

QUnit.test("Can handle im_status of unknown partner", async (assert) => {
    const { env, pyEnv } = await start();
    const partnerId = pyEnv["res.partner"].create({ name: "Bob" });
    pyEnv["bus.bus"]._sendone("channel-1", "mail.record/insert", {
        Partner: { im_status: "online", id: partnerId },
    });
    await nextTick();
    const persona = env.services["mail.store"].personas[createLocalId("partner", partnerId)];
    assert.ok(persona);
    assert.ok(persona.im_status === "online");
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
