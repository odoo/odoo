/** @odoo-module **/

import { UPDATE_BUS_PRESENCE_DELAY } from "@bus/im_status_service";
import { start, startServer, afterNextRender } from "@mail/../tests/helpers/test_utils";
import { createLocalId } from "@mail/new/utils/misc";
import { getFixture, nextTick } from "@web/../tests/helpers/utils";

let target;

QUnit.module("im status", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("initially online", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-partner-im-status-icon.o-online");
});

QUnit.test("initially offline", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-partner-im-status-icon.o-offline");
});

QUnit.test("initially away", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-partner-im-status-icon.o-away");
});

QUnit.test("change icon on change partner im_status", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-partner-im-status-icon.o-online");

    pyEnv["res.partner"].write([partnerId], { im_status: "offline" });
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.containsOnce(target, ".o-mail-partner-im-status-icon.o-offline");

    pyEnv["res.partner"].write([partnerId], { im_status: "away" });
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.containsOnce(target, ".o-mail-partner-im-status-icon.o-away");

    pyEnv["res.partner"].write([partnerId], { im_status: "online" });
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.containsOnce(target, ".o-mail-partner-im-status-icon.o-online");
});

QUnit.test("Can handle im_status of unknown partner", async function (assert) {
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
