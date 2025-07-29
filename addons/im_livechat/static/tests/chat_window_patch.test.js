import {
    click,
    contains,
    openDiscuss,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { rpc } from "@web/core/network/rpc";

defineLivechatModels();

test.tags("desktop");
test("closing a chat window with no message from admin side unpins it", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                unpin_dt: false,
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "livechat",
        uuid: "channel-10-uuid",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await click(".o-mail-ChatWindow-command[title*='Close Chat Window']", {
        parent: [".o-mail-ChatWindow", { text: "Demo" }],
    });
    await contains(".o_notification", { text: "You unpinned your conversation with Demo" });
});

test.tags("desktop");
test("Show livechats with new message in chat hub even when in discuss app)", async () => {
    // Chat hub show conversations with new message only when outside of discuss app by default.
    // Live chats are special in that agents are expected to see their ongoing conversations at all
    // time. Closing chat window ends the conversation. Hence the livechat always are shown on chat hub.
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const [livechatId, channelId] = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ guest_id: guestId }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
        },
        {
            channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
            channel_type: "channel",
            name: "general",
        },
    ]);
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Test</p>",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message:contains('Test')");
    // simulate livechat visitor sending a message
    await withGuest(guestId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "Hello, I need help!",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: livechatId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-DiscussSidebar-item:contains('Visitor 11') .badge", { text: "1" });
    await openFormView("res.partner", serverState.partnerId);
    await contains(".o-mail-ChatWindow-header:contains('Visitor 11')");
});
