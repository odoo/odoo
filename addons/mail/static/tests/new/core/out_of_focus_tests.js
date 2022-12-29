/** @odoo-module */

import { start } from "@mail/../tests/helpers/test_utils";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { makeFakePresenceService } from "@bus/../tests/helpers/mock_services";
import { nextTick } from "@web/../tests/helpers/utils";

QUnit.module("out of focus");

QUnit.test("Spaces in notifications are not encoded", async function (assert) {
    const { env, openDiscuss, pyEnv } = await start({
        services: {
            notification: makeFakeNotificationService((message) => assert.step(message)),
            presence: makeFakePresenceService({ isOdooFocused: () => false }),
        },
    });
    const channelId = pyEnv["mail.channel"].create({ channel_type: "chat" });
    await openDiscuss();
    await env.services.rpc("/mail/message/post", {
        post_data: {
            body: "Hello world!",
            attachment_ids: [],
        },
        thread_id: channelId,
        thread_model: "mail.channel",
    });
    await nextTick();
    assert.verifySteps(["Hello world!"]);
});
