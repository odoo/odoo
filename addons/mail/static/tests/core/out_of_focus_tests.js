/** @odoo-module */

import { start } from "@mail/../tests/helpers/test_utils";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { makeFakePresenceService } from "@bus/../tests/helpers/mock_services";
import { nextTick } from "@web/../tests/helpers/utils";

QUnit.module("out of focus");

QUnit.test("Spaces in notifications are not encoded", async (assert) => {
    const { openDiscuss, pyEnv } = await start({
        services: {
            notification: makeFakeNotificationService((message) => assert.step(message)),
            presence: makeFakePresenceService({ isOdooFocused: () => false }),
        },
    });
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const channel = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]])[0];
    await openDiscuss();
    pyEnv["bus.bus"]._sendone(channel, "discuss.channel/new_message", {
        id: channelId,
        message: {
            body: "Hello world!",
            id: 126,
            model: "discuss.channel",
            res_id: channelId,
        },
    });
    await nextTick();
    assert.verifySteps(["Hello world!"]);
});
