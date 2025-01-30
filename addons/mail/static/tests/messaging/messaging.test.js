import {
    contains,
    defineMailModels,
    insertText,
    onRpcBefore,
    openDiscuss,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import {
    asyncStep,
    Command,
    serverState,
    waitForSteps,
    withUser,
} from "@web/../tests/web_test_helpers";
import { press } from "@odoo/hoot-dom";

import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("Receiving a new message out of discuss app should open a chat bubble", async () => {
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
    onRpcBefore("/web/dataset/call_kw/ir.http/lazy_session_info", (args) => {
        asyncStep("init_messaging");
    });
    await start();
    await waitForSteps(["init_messaging"]);
    // send after init_messaging because bus subscription is done after init_messaging
    // simulate receving new message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Magic!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatBubble[name='Dumbledore']");
});

test("Receiving a new message in discuss app should open a chat bubble after leaving discuss app", async () => {
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
    onRpcBefore("/web/dataset/call_kw/ir.http/lazy_session_info", (args) => {
        asyncStep("init_messaging");
    });
    await start();
    await waitForSteps(["init_messaging"]);
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
    await contains(".o-mail-ChatBubble[name='Dumbledore']");
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
    await press("Enter");
    // leaving discuss.
    await openFormView("res.partner", partnerId);
    // weak test, no guarantee that we waited long enough for the potential chat window to open
    await contains(".o-mail-ChatWindow", { count: 0, text: "Dumbledore" });
});
