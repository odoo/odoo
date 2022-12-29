/** @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { makeFakePresenceService } from "@bus/../tests/helpers/mock_services";
import { start } from "@mail/../tests/helpers/test_utils";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { nextTick } from "@web/../tests/helpers/utils";

QUnit.module("messaging service");

QUnit.test("Notify message received out of focus", async (assert) => {
    const pyEnv = await startServer();
    const senderId = pyEnv["res.users"].create({ name: "Bob" });
    const channelId = pyEnv["mail.channel"].create({
        name: "Livechat 1",
        channel_type: "livechat",
    });
    const [channel] = pyEnv["mail.channel"].searchRead([["id", "=", channelId]]);
    const { env } = await start({
        services: {
            notification: makeFakeNotificationService((message, { title }) => {
                assert.step(`message - ${message}`);
                assert.step(`title - ${title}`);
            }),
            presence: makeFakePresenceService({
                isOdooFocused() {
                    return false;
                },
            }),
        },
    });
    await env.services.rpc("/mail/chat_post", {
        context: { mockedUserId: senderId },
        message_content: "Hello",
        uuid: channel.uuid,
    });
    await nextTick();
    assert.verifySteps(["message - Hello", "title - New message"]);
});
