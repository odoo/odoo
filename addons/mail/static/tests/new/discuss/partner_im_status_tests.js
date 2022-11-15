/** @odoo-module **/

import { UPDATE_BUS_PRESENCE_DELAY } from "@bus/im_status_service";
import { start, startServer, afterNextRender } from "@mail/../tests/helpers/test_utils";
import { getFixture } from "@web/../tests/helpers/utils";

let target;

QUnit.module("mail", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
    });

    QUnit.module("partner im_status");

    QUnit.test("initially online", async function (assert) {
        assert.expect(1);

        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ im_status: "online" });
        const mailChannelId = pyEnv["mail.channel"].create({ name: "TestChanel" });
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId,
        });
        const { advanceTime, openDiscuss } = await start({
            discuss: {
                params: {
                    default_active_id: `mail.channel_${mailChannelId}`,
                },
            },
            hasTimeControl: true,
        });
        await openDiscuss();
        await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
        assert.containsOnce(target, ".o-mail-partner-im-status-icon.o-online");
    });

    QUnit.test("initially offline", async function (assert) {
        assert.expect(1);

        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ im_status: "offline" });
        const mailChannelId = pyEnv["mail.channel"].create({ name: "TestChannel" });
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId,
        });
        const { advanceTime, openDiscuss } = await start({
            discuss: {
                params: {
                    default_active_id: `mail.channel_${mailChannelId}`,
                },
            },
            hasTimeControl: true,
        });
        await openDiscuss();
        await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
        assert.containsOnce(target, ".o-mail-partner-im-status-icon.o-offline");
    });

    QUnit.test("initially away", async function (assert) {
        assert.expect(1);

        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ im_status: "away" });
        const mailChannelId = pyEnv["mail.channel"].create({ name: "TestChanel" });
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId,
        });
        const { advanceTime, openDiscuss } = await start({
            discuss: {
                params: {
                    default_active_id: `mail.channel_${mailChannelId}`,
                },
            },
            hasTimeControl: true,
        });
        await openDiscuss();
        await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
        assert.containsOnce(target, ".o-mail-partner-im-status-icon.o-away");
    });

    QUnit.test("change icon on change partner im_status", async function (assert) {
        assert.expect(4);

        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ im_status: "online" });
        const mailChannelId = pyEnv["mail.channel"].create({ name: "TestChannel" });
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId,
        });
        const { advanceTime, openDiscuss } = await start({
            discuss: {
                params: {
                    default_active_id: `mail.channel_${mailChannelId}`,
                },
            },
            hasTimeControl: true,
        });
        await openDiscuss();
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
});
