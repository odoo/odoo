/** @odoo-module alias=@mail/../tests/core/out_of_focus_tests default=false */
const test = QUnit.test; // QUnit.test()

import { serverState, startServer } from "@bus/../tests/helpers/mock_python_environment";
import { makeFakePresenceService } from "@bus/../tests/helpers/mock_services";

import { start } from "@mail/../tests/helpers/test_utils";

import { assertSteps, contains, step } from "@web/../tests/utils";

QUnit.module("out of focus");

test("Spaces in notifications are not encoded", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const channel = pyEnv["discuss.channel"].search_read([["id", "=", channelId]])[0];
    await start({
        async mockRPC(route, args, originalRpc) {
            if (route === "/mail/action" && args.init_messaging) {
                const res = await originalRpc(...arguments);
                step(`/mail/action - ${JSON.stringify(args)}`);
                return res;
            }
        },
        services: {
            presence: makeFakePresenceService({ isOdooFocused: () => false }),
        },
    });
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId },
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
