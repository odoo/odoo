/** @odoo-module */

import { test } from "@odoo/hoot";
import { assertSteps, contains, start, startServer, step } from "../mail_test_helpers";
import { constants, mockService, onRpc } from "@web/../tests/web_test_helpers";

test.skip("Spaces in notifications are not encoded", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const [channel] = pyEnv["discuss.channel"].search_read([["id", "=", channelId]]);
    onRpc(async (route, args) => {
        if (route === "/mail/action" && args.init_messaging) {
            step(`/mail/action - ${JSON.stringify(args)}`);
        }
    });
    mockService("presence", () => ({
        start() {
            return {
                ...super.start(),
                isOdooFocused: () => false,
            };
        },
    }));
    await start();
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: constants.USER_ID },
        })}`,
    ]);
    // send after init_messaging because bus subscription is done after init_messaging
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
