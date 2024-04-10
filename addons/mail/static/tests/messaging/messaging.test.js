import { describe, test } from "@odoo/hoot";

/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;
import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    insertText,
    onRpcBefore,
    openDiscuss,
    openFormView,
    start,
    startServer,
    step,
} from "../mail_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { withUser } from "@web/../tests/_framework/mock_server/mock_server";
import { rpcWithEnv } from "@mail/utils/common/misc";

describe.current.tags("desktop");
defineMailModels();

test("Receiving a new message out of discuss app should open a chat window", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    onRpcBefore("/mail/action", (args) => {
        if (args.init_messaging) {
            step(`/mail/action - ${JSON.stringify(args)}`);
        }
    });
    const env = await start();
    rpc = rpcWithEnv(env);
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
    ]);
    // send after init_messaging because bus subscription is done after init_messaging
    // simulate receving new message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Magic!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow", { text: "Dumbledore" });
});

test("Receiving a new message in discuss app should open a chat window after leaving discuss app", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    onRpcBefore("/mail/action", (args) => {
        if (args.init_messaging) {
            step(`/mail/action - ${JSON.stringify(args)}`);
        }
    });
    const env = await start();
    rpc = rpcWithEnv(env);
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
    ]);
    // send after init_messaging because bus subscription is done after init_messaging
    await openDiscuss();
    // simulate receiving new message
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Tricky", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    // leaving discuss.
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-ChatWindow", { text: "Dumbledore" });
});

test("Posting a message in discuss app should not open a chat window after leaving discuss app", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
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
