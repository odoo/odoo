/** @odoo-module */

import { test } from "@odoo/hoot";

import { rpc } from "@web/core/network/rpc";
import {
    assertSteps,
    click,
    contains,
    insertText,
    openDiscuss,
    openFormView,
    start,
    startServer,
    step,
} from "../mail_test_helpers";
import { Command, constants, onRpc } from "@web/../tests/web_test_helpers";

test.skip("Receiving a new message out of discuss app should open a chat window", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    onRpc((route, args) => {
        if (route === "/mail/action" && args.init_messaging) {
            step(`/mail/action - ${JSON.stringify(args)}`);
        }
    });
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
    // simulate receving new message
    pyEnv.withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "new message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow", { text: "Dumbledore" });
});

test.skip("Receiving a new message in discuss app should open a chat window after leaving discuss app", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    onRpc((route, args) => {
        if (route === "/mail/action" && args.init_messaging) {
            step(`/mail/action - ${JSON.stringify(args)}`);
        }
    });
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
    await openDiscuss();
    // simulate receiving new message
    pyEnv.withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "new message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    // leaving discuss.
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-ChatWindow", { text: "Dumbledore" });
});

test.skip("Posting a message in discuss app should not open a chat window after leaving discuss app", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "test https://www.odoo.com/");
    await click(".o-mail-Composer-send:enabled");
    // leaving discuss.
    await openFormView("res.partner", partnerId);
    // weak test, no guarantee that we waited long enough for the potential chat window to open
    await contains(".o-mail-ChatWindow", { count: 0, text: "Dumbledore" });
});
