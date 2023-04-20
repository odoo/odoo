/** @odoo-module **/

import { UPDATE_BUS_PRESENCE_DELAY } from "@bus/im_status_service";

import { start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("im_status");

QUnit.test("on leave & online", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "leave_online" });
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { advanceTime, afterNextRender, openDiscuss } = await start({
        hasTimeControl: true,
    });
    await openDiscuss(channelId);
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.containsOnce($, ".o-mail-ImStatus i.fa-plane[title='Online']");
});

QUnit.test("on leave & away", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "leave_away" });
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { advanceTime, afterNextRender, openDiscuss } = await start({
        hasTimeControl: true,
    });
    await openDiscuss(channelId);
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.containsOnce($, ".o-mail-ImStatus i.fa-plane[title='Idle']");
});

QUnit.test("on leave & offline", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "leave_offline" });
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { advanceTime, afterNextRender, openDiscuss } = await start({
        hasTimeControl: true,
    });
    await openDiscuss(channelId);
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.containsOnce($, ".o-mail-ImStatus i.fa-plane[title='Out of office']");
});
