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
        if (args.init_messaging) {
<<<<<<< master
            asyncStep(`/mail/data - ${JSON.stringify(args)}`);
||||||| 760a6df27f099a596ed35efde41f7fc2b6479fb6
            step(`/mail/action - ${JSON.stringify(args)}`);
=======
            step(`/mail/data - ${JSON.stringify(args)}`);
>>>>>>> 0eea914ec97919688ced2176325e44df8e2c5d63
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
<<<<<<< master
    await waitForSteps([
||||||| 760a6df27f099a596ed35efde41f7fc2b6479fb6
    await assertSteps([
        `/mail/action - ${JSON.stringify({
=======
    await assertSteps([
>>>>>>> 0eea914ec97919688ced2176325e44df8e2c5d63
        `/mail/data - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
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
