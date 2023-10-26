/* @odoo-module */

import { makeFakePresenceService } from "@bus/../tests/helpers/mock_services";

import { start } from "@mail/../tests/helpers/test_utils";

import { contains } from "@web/../tests/utils";

QUnit.module("out of focus");

QUnit.test("Spaces in notifications are not encoded", async () => {
    const { openDiscuss, pyEnv } = await start({
        services: {
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
    await contains(".o_notification:has(.o_notification_bar.bg-info)", { text: "Hello world!" });
});
