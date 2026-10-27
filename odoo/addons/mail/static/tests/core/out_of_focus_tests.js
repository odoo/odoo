/* @odoo-module */

import { makeFakePresenceService } from "@bus/../tests/helpers/mock_services";
import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { contains } from "@web/../tests/utils";

QUnit.module("out of focus");

QUnit.test("Spaces in notifications are not encoded", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const channel = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]])[0];
    const { openDiscuss } = await start({
        services: {
            presence: makeFakePresenceService({ isOdooFocused: () => false }),
        },
    });
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
    await contains(".o_notification.border-info", { text: "Hello world!" });
});
