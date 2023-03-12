/** @odoo-module **/

import { UPDATE_BUS_PRESENCE_DELAY } from "@bus/im_status_service";
import { start, startServer, afterNextRender } from "@mail/../tests/helpers/test_utils";
import { createLocalId } from "@mail/new/utils/misc";
import { nextTick } from "@web/../tests/helpers/utils";

QUnit.module("im status");

QUnit.test("initially online", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ im_status: "online" });
    const channelId = pyEnv["mail.channel"].create({ name: "TestChanel" });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "mail.channel",
        res_id: channelId,
    });
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss(channelId);
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.containsOnce($, ".o-mail-ImStatus i[title='Online']");
});

QUnit.test("initially offline", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ im_status: "offline" });
    const channelId = pyEnv["mail.channel"].create({ name: "TestChannel" });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "mail.channel",
        res_id: channelId,
    });
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss(channelId);
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.containsOnce($, ".o-mail-ImStatus i[title='Offline']");
});

QUnit.test("initially away", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ im_status: "away" });
    const channelId = pyEnv["mail.channel"].create({ name: "TestChanel" });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "mail.channel",
        res_id: channelId,
    });
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss(channelId);
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.containsOnce($, ".o-mail-ImStatus i[title='Idle']");
});

QUnit.test("change icon on change partner im_status", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ im_status: "online" });
    const channelId = pyEnv["mail.channel"].create({ name: "TestChannel" });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "mail.channel",
        res_id: channelId,
    });
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss(channelId);
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.containsOnce($, ".o-mail-ImStatus i[title='Online']");

    pyEnv["res.partner"].write([partnerId], { im_status: "offline" });
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.containsOnce($, ".o-mail-ImStatus i[title='Offline']");

    pyEnv["res.partner"].write([partnerId], { im_status: "away" });
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.containsOnce($, ".o-mail-ImStatus i[title='Idle']");

    pyEnv["res.partner"].write([partnerId], { im_status: "online" });
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.containsOnce($, ".o-mail-ImStatus i[title='Online']");
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
