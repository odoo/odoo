import {
    contains,
    defineMailModels,
    onRpcBefore,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import {
    asyncStep,
    Command,
    mockService,
    serverState,
    waitForSteps,
    withUser,
} from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("Spaces in notifications are not encoded", async () => {
    onRpcBefore("/mail/data", (args) => {
        if (args.fetch_params.includes("init_messaging")) {
            asyncStep(`/mail/data - ${JSON.stringify(args)}`);
        }
    });
    mockService("presence", { isOdooFocused: () => false });
    const pyEnv = await startServer();
    const bobUserId = pyEnv["res.users"].create({ name: "bob" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "bob", user_ids: [bobUserId] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: bobPartnerId }),
        ],
    });
    await start();
    await waitForSteps([
        `/mail/data - ${JSON.stringify({
            fetch_params: ["failures", "systray_get_activities", "init_messaging"],
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
    ]);
    await openDiscuss();
    await withUser(bobUserId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello world!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o_notification:has(.o_notification_bar.bg-info)", { text: "Hello world!" });
});
