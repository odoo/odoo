import {
    click,
    contains,
    openDiscuss,
    openFormView,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { rpc } from "@web/core/network/rpc";
import { defineLivechatModels } from "./livechat_test_helpers";

defineLivechatModels();

test.tags("mobile");
test("can fold livechat chat windows in mobile", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Visitor" });
    pyEnv["res.users"].create([{ partner_id: partnerId }]);
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                unpin_dt: false,
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "livechat",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Visitor" });
    await click(".o-mail-ChatWindow-command[title*='Fold']", {
        parent: [".o-mail-ChatWindow", { text: "Visitor" }],
    });
    await contains(".o-mail-ChatBubble");
});

test.tags("desktop");
test("closing a chat window with no message from admin side unpins it", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Partner 1" },
        { name: "Partner 2" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                unpin_dt: false,
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId_1 }),
        ],
        channel_type: "livechat",
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                unpin_dt: false,
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId_2 }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Partner 2" });
    await click(".o-mail-ChatWindow-command[title*='Close Chat Window']", {
        parent: [".o-mail-ChatWindow", { text: "Partner 2" }],
    });
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "Partner 1" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "Partner 2" });
});

test.tags("desktop", "focus required");
test("Focus should not be stolen when a new livechat open", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 12" });
    const channelIds = pyEnv["discuss.channel"].create([
        { name: "general" },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                }),
                Command.create({ guest_id: guestId }),
            ],
            channel_type: "livechat",
            livechat_active: true,
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "general" });
    await contains(".o-mail-ChatWindow", { text: "general" });
    await contains(".o-mail-Composer-input[placeholder='Message #general…']:focus");
    withGuest(guestId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "hu",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelIds[1],
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow", { text: "Visitor 12" });
    await animationFrame();
    await contains(".o-mail-Composer-input[placeholder='Message #general…']:focus");
});

test("do not ask confirmation if other operators are present", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor #12" });
    const otherOperatorId = pyEnv["res.partner"].create({ name: "John" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
            Command.create({ partner_id: otherOperatorId }),
        ],
        livechat_operator_id: serverState.partnerId,
        channel_type: "livechat",
        livechat_active: true,
    });
    setupChatHub({ opened: [channelId] });
    await start();
    await contains(".o-mail-ChatWindow");
    await click("[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
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
