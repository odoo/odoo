import {
    click,
    contains,
    focus,
    insertText,
    openDiscuss,
    patchUiSize,
    setupChatHub,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { animationFrame, press } from "@odoo/hoot-dom";
import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";
import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineLivechatModels();

test("tab on discuss composer goes to oldest unread livechat", async () => {
    const pyEnv = await startServer();
    const guestId_1 = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const guestId_2 = pyEnv["mail.guest"].create({ name: "Visitor 12" });
    const guestId_3 = pyEnv["mail.guest"].create({ name: "Visitor 13" });
    const channelIds = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ guest_id: guestId_1 }),
            ],
            channel_type: "livechat",
            livechat_active: true,
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    message_unread_counter: 1,
                    last_interest_dt: "2021-01-02 10:00:00",
                }),
                Command.create({ guest_id: guestId_2 }),
            ],
            channel_type: "livechat",
            livechat_active: true,
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 2",
        },
        {
            anonymous_name: "Visitor 13",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    message_unread_counter: 1,
                    last_interest_dt: "2021-01-01 10:00:00",
                }),
                Command.create({ guest_id: guestId_3 }),
            ],
            channel_type: "livechat",
            livechat_active: true,
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 3",
        },
    ]);
    pyEnv["mail.message"].create([
        {
            author_guest_id: guestId_2,
            body: "Hello",
            model: "discuss.channel",
            res_id: channelIds[1],
        },
        {
            author_guest_id: guestId_3,
            body: "Hello",
            model: "discuss.channel",
            res_id: channelIds[2],
        },
    ]);
    await start();
    await openDiscuss(channelIds[0]);
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Visitor 11" });
    await contains(".o-mail-Composer-footer", { text: "Tab to next livechat" });
    await focus(".o-mail-Composer-input");
    await contains(".o-active .o-mail-DiscussSidebar-badge", { count: 0 });
    triggerHotkey("Tab");
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Visitor 13" });
    await focus(".o-mail-Composer-input");
    await contains(".o-active .o-mail-DiscussSidebar-badge", { count: 0 });
    triggerHotkey("Tab");
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Visitor 12" });
});

test("Tab livechat picks ended livechats last", async () => {
    const pyEnv = await startServer();
    const guestIds = pyEnv["mail.guest"].create([
        { name: "Visitor 0" },
        { name: "Visitor 1" },
        { name: "Visitor 2" },
        { name: "Visitor 3" },
        { name: "Visitor 4" },
    ]);
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        name: "Test",
        user_ids: [serverState.userId],
    });
    const channelIds = pyEnv["discuss.channel"].create(
        guestIds.map((guestId) => ({
            channel_type: "livechat",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    last_interest_dt: "2021-01-02 10:00:00",
                }),
                Command.create({ guest_id: guestId }),
            ],
            livechat_active: true,
            livechat_channel_id: livechatChannelId,
            livechat_operator_id: serverState.partnerId,
            create_uid: serverState.publicUserId,
        }))
    );
    patchUiSize({ width: 1920 });
    setupChatHub({ folded: [channelIds[0], channelIds[1], channelIds[2], channelIds[3]] });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Visitor 4" });
    await contains(".o-mail-ChatWindow", { text: "Visitor 4" });
    await contains(".o-mail-Composer-input[placeholder='Message Visitor 4…']:focus");
    await withGuest(guestIds[1], () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "livechat 1",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelIds[1],
            thread_model: "discuss.channel",
        })
    );
    await withGuest(guestIds[1], () =>
        rpc("/im_livechat/visitor_leave_session", { channel_id: channelIds[1] })
    );
    await withGuest(guestIds[3], () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "livechat 3",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelIds[3],
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatBubble-counter", { text: "1", count: 2 });
    await press("Tab");
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatWindow", { text: "Visitor 3" });
    await contains(".o-mail-Composer-input[placeholder='Message Visitor 3…']:focus");
    await withGuest(guestIds[0], () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "livechat 0",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelIds[0],
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatBubble-counter", { text: "1", count: 2 });
    await press("Tab");
    await contains(".o-mail-ChatWindow", { count: 3 });
    await contains(".o-mail-ChatWindow", { text: "Visitor 0" });
    await withGuest(guestIds[2], () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "livechat 2",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelIds[2],
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatBubble-counter", { text: "1", count: 2 });
    await press("Tab");
    await contains(".o-mail-ChatWindow", { text: "Visitor 2" });
    await animationFrame();
    await press("Tab");
    // Ensure the last tab selection is an ended livechat
    await contains(".o-mail-ChatWindow", { text: "Visitor 1" });
    await contains("span", { text: "This livechat conversation has ended" });
});

test.tags("focus required");
test("switching to folded chat window unfolds it", async () => {
    const pyEnv = await startServer();
    const guestId_1 = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const guestId_2 = pyEnv["mail.guest"].create({ name: "Visitor 12" });
    const channelIds = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ guest_id: guestId_1 }),
            ],
            channel_type: "livechat",
            livechat_active: true,
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    last_interest_dt: "2021-01-02 10:00:00",
                }),
                Command.create({ guest_id: guestId_2 }),
            ],
            channel_type: "livechat",
            livechat_active: true,
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 2",
        },
    ]);
    pyEnv["mail.message"].create({
        author_guest_id: guestId_2,
        body: "Hello",
        model: "discuss.channel",
        res_id: channelIds[1],
    });
    setupChatHub({ opened: [channelIds[0]], folded: [channelIds[1]] });
    await start();
    await contains(".o-mail-ChatBubble[name='Visitor 12']");
    await focus(".o-mail-Composer-input", {
        parent: [".o-mail-ChatWindow", { text: "Visitor 11" }],
    });
    triggerHotkey("Tab");
    await contains(".o-mail-ChatWindow", {
        text: "Visitor 12",
        contains: [".o-mail-Composer-input:focus"],
    });
});

test.tags("focus required");
test("switching to hidden chat window unhides it", async () => {
    const pyEnv = await startServer();
    const [guestId_1, guestId_2] = pyEnv["mail.guest"].create([
        { name: "Visitor 11" },
        { name: "Visitor 12" },
    ]);
    const channelIds = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ guest_id: guestId_1 }),
            ],
            channel_type: "livechat",
            livechat_active: true,
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    last_interest_dt: "2021-01-02 10:00:00",
                }),
                Command.create({ guest_id: guestId_2 }),
            ],
            channel_type: "livechat",
            livechat_active: true,
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 2",
        },
        { name: "general" },
    ]);
    const [livechat_1] = channelIds;
    pyEnv["mail.message"].create({
        author_guest_id: guestId_2,
        body: "Hello",
        model: "discuss.channel",
        res_id: livechat_1,
    });
    setupChatHub({ opened: channelIds.reverse() });
    patchUiSize({ width: 900 }); // enough for 2 chat windows max
    await start();
    // FIXME: expected order: general, 12, 11
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatWindow", { count: 0, text: "Visitor 11" });
    await focus(".o-mail-Composer-input", {
        parent: [".o-mail-ChatWindow", { text: "Visitor 12" }],
    });
    triggerHotkey("Tab");
    await contains(".o-mail-ChatWindow", {
        text: "Visitor 11",
        contains: [".o-mail-Composer-input:focus"],
    });
});

test("tab on composer doesn't switch thread if user is typing", async () => {
    const pyEnv = await startServer();
    const guestId_1 = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const guestId_2 = pyEnv["mail.guest"].create({ name: "Visitor 12" });
    const channelIds = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ guest_id: guestId_1 }),
            ],
            channel_type: "livechat",
            livechat_active: true,
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    message_unread_counter: 1,
                    last_interest_dt: "2021-01-02 10:00:00",
                }),
                Command.create({ guest_id: guestId_2 }),
            ],
            channel_type: "livechat",
            livechat_active: true,
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 2",
        },
    ]);
    await start();
    await openDiscuss(channelIds[0]);
    await insertText(".o-mail-Composer-input", "Hello, ");
    triggerHotkey("Tab");
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Visitor 11" });
});

test("tab on composer doesn't switch thread if no unread thread", async () => {
    const pyEnv = await startServer();
    const guestId_1 = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const guestId_2 = pyEnv["mail.guest"].create({ name: "Visitor 12" });
    const channelIds = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ guest_id: guestId_1 }),
            ],
            channel_type: "livechat",
            livechat_active: true,
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ guest_id: guestId_2 }),
            ],
            channel_type: "livechat",
            livechat_active: true,
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 2",
        },
    ]);
    await start();
    await openDiscuss(channelIds[0]);
    await focus(".o-mail-Composer-input");
    triggerHotkey("Tab");
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Visitor 11" });
});
