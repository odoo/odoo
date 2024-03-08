import { describe, test } from "@odoo/hoot";
import {
    assertSteps,
    contains,
    defineMailModels,
    onRpcBefore,
    start,
    startServer,
    step,
} from "../mail_test_helpers";
import { mockService, serverState } from "@web/../tests/web_test_helpers";
import { presenceService } from "@bus/services/presence_service";

describe.current.tags("desktop");
defineMailModels();

test("Spaces in notifications are not encoded", async () => {
    onRpcBefore("/mail/action", (args) => {
        if (args.init_messaging) {
            step(`/mail/action - ${JSON.stringify(args)}`);
        }
    });
    mockService("presence", () => ({
        ...presenceService.start(),
        isOdooFocused: () => false,
    }));
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const channel = pyEnv["discuss.channel"].search_read([["id", "=", channelId]])[0];
    await start();
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
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
