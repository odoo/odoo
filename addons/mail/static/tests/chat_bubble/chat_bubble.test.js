import { describe, expect, test } from "@odoo/hoot";
import { leave, runAllTimers } from "@odoo/hoot-dom";
import { Command, serverState, withUser } from "@web/../tests/web_test_helpers";
import {
    assertChatHub,
    click,
    contains,
    defineMailModels,
    hover,
    insertText,
    onRpcBefore,
    openDiscuss,
    openFormView,
    patchUiSize,
    setupChatHub,
    SIZES,
    start,
    startServer,
    triggerEvents,
    triggerHotkey,
} from "../mail_test_helpers";

import { rpc } from "@web/core/network/rpc";
import { range } from "@web/core/utils/numbers";

describe.current.tags("desktop");
defineMailModels();

test("Folded chat windows are displayed as chat bubbles", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([
        { name: "Channel A" },
        { name: "Channel B" },
    ]);
    setupChatHub({ folded: channelIds });
    await start();
    await contains(".o-mail-ChatBubble", { count: 2 });
    await click(".o-mail-ChatBubble", { count: 2 });
    await contains(".o-mail-ChatBubble", { count: 1 });
    await contains(".o-mail-ChatWindow", { count: 1 });
});

test.tags("focus required");
test("No duplicated chat bubbles", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    // Make bubble of "John" chat
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu button", { text: "New Message" });
    await insertText("input[placeholder='Search a conversation']", "John");
    await click(".o_command_name", { text: "John" });
    await contains(".o-mail-ChatWindow", { text: "John" });
    await contains(".o-mail-ChatWindow", { text: "This is the start of direct chat with John" }); // wait fully loaded
    await click("button[title='Fold']");
    await contains(".o-mail-ChatBubble[name='John']");
    // Make bubble of "John" chat again
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu button", { text: "New Message" });
    await insertText("input[placeholder='Search a conversation']", "John");
    await click(".o_command_name", { text: "John" });
    await contains(".o-mail-ChatBubble[name='John']", { count: 0 });
    await contains(".o-mail-ChatWindow", { text: "John" });
    await click(".o-mail-ChatWindow-header [title='Fold']");
    // Make again from click messaging menu item
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatBubble[name='John']", { count: 0 });
    await contains(".o-mail-ChatWindow", { text: "John" });
});

test("Up to 7 chat bubbles", async () => {
    const pyEnv = await startServer();
    const channelIds = [];
    for (let i = 1; i <= 8; i++) {
        channelIds.push(pyEnv["discuss.channel"].create({ name: String(i) }));
    }
    setupChatHub({ folded: channelIds.reverse() });
    await start();
    for (let i = 8; i > 1; i--) {
        await contains(`.o-mail-ChatBubble[name='${String(i)}']`);
    }
    await contains(".o-mail-ChatBubble[name='1']", { count: 0 });
    await contains(".o-mail-ChatHub-hiddenBtn", { text: "+1" });
    await hover(".o-mail-ChatHub-hiddenBtn");
    await contains(".o-mail-ChatHub-hiddenItem[name='1']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o-mail-ChatHub-hiddenItem");
    await contains(".o-mail-ChatWindow", { count: 1 });
    await contains(".o-mail-ChatHub-hiddenBtn", { count: 0 });
});

test("Ordering of chat bubbles is consistent and seems logical.", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const channelIds = [channelId];
    for (let i = 1; i <= 7; i++) {
        channelIds.push(pyEnv["discuss.channel"].create({ name: String(i) }));
    }
    setupChatHub({ folded: channelIds.reverse() });
    await start();
    // FIXME: expect arbitrary order 7, 6, 5, 4, 3, 2, 1
    await contains(":nth-child(1 of .o-mail-ChatBubble)[name='7']");
    await contains(":nth-child(2 of .o-mail-ChatBubble)[name='6']");
    await contains(":nth-child(3 of .o-mail-ChatBubble)[name='5']");
    await contains(":nth-child(4 of .o-mail-ChatBubble)[name='4']");
    await contains(":nth-child(5 of .o-mail-ChatBubble)[name='3']");
    await contains(":nth-child(6 of .o-mail-ChatBubble)[name='2']");
    await contains(":nth-child(7 of .o-mail-ChatBubble)[name='1']");
    await contains(".o-mail-ChatBubble[name='Demo']", { count: 0 });
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o-mail-ChatBubble[name='3']");
    await contains(".o-mail-ChatWindow", { text: "3" });
    await contains(":nth-child(7 of .o-mail-ChatBubble)[name='Demo']");
    await click(".o-mail-ChatWindow-header [title='Fold']");
    await contains(".o-mail-ChatBubble[name='Demo']", { count: 0 });
    await click(".o-mail-ChatBubble[name='4']");
    await contains(":nth-child(1 of .o-mail-ChatBubble)[name='3']");
    await contains(":nth-child(2 of .o-mail-ChatBubble)[name='7']");
    await contains(":nth-child(3 of .o-mail-ChatBubble)[name='6']");
    await contains(":nth-child(7 of .o-mail-ChatBubble)[name='Demo']");
    await click(".o-mail-ChatWindow-header [title='Fold']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    // no reorder on receiving new message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "test", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await hover(".o-mail-ChatHub-hiddenBtn");
    await contains(".o-mail-ChatHub-hiddenItem[name='Demo']");
});

test("Hover on chat bubble shows chat name + last message preview", async () => {
    const pyEnv = await startServer();
    const marcPartnerId = pyEnv["res.partner"].create({ name: "Marc" });
    const marcChannelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: marcPartnerId }),
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        body: "Hello!",
        model: "discuss.channel",
        author_id: marcPartnerId,
        res_id: marcChannelId,
    });
    const demoPartnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const demoChannelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: demoPartnerId }),
        ],
        channel_type: "chat",
    });
    setupChatHub({ folded: [marcChannelId, demoChannelId] });
    await start();
    await hover(".o-mail-ChatBubble[name='Marc']");
    await contains(".o-mail-ChatBubble-preview", { text: "MarcHello!" });
    await leave();
    await contains(".o-mail-ChatBubble-preview", { count: 0 });
    await hover(".o-mail-ChatBubble[name='Demo']");
    await contains(".o-mail-ChatBubble-preview", { text: "Demo" });
    await leave();
    rpc("/mail/message/post", {
        post_data: { body: "Hi", message_type: "comment" },
        thread_id: demoChannelId,
        thread_model: "discuss.channel",
    });
    await hover(".o-mail-ChatBubble[name='Demo']");
    await contains(".o-mail-ChatBubble-preview", { text: "DemoYou: Hi" });
});

test("Chat bubble preview works on author as email address", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["discuss.channel"].create({ name: "test channel" });
    const messageId = pyEnv["mail.message"].create({
        author_id: null,
        body: "Some email message",
        email_from: "md@oilcompany.fr",
        model: "discuss.channel",
        needaction: true,
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await click(".o-mail-ChatWindow [title='Fold']");
    await hover(".o-mail-ChatBubble");
    await contains(".o-mail-ChatBubble-preview", { text: "md@oilcompany.fr: Some email message" });
});

test("chat bubbles are synced between tabs", async () => {
    const pyEnv = await startServer();
    const marcPartnerId = pyEnv["res.partner"].create({ name: "Marc" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: marcPartnerId }),
        ],
        channel_type: "chat",
    });
    setupChatHub({ folded: [channelId] });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    await contains(".o-mail-ChatBubble", { target: tab1 });
    await contains(".o-mail-ChatBubble", { target: tab2 });
    await runAllTimers(); // Wait for bus service to fully load
    await click(".o-mail-ChatBubble[name='Marc']", { target: tab1 });
    await contains(".o-mail-ChatWindow", { target: tab2 }); // open sync
    await click(".o-mail-ChatWindow-header [title='Fold']", { target: tab2 });
    await contains(".o-mail-ChatWindow", { target: tab1, count: 0 }); // fold sync
    await click(".o-mail-ChatBubble[name='Marc'] .o-mail-ChatBubble-close", { target: tab1 });
    await contains(".o-mail-ChatBubble[name='Marc']", { target: tab2, count: 0 }); // close sync
});

test("Chat bubbles do not fetch messages until becoming open", async () => {
    const pyEnv = await startServer();
    const [channeId1, channelId2] = pyEnv["discuss.channel"].create([
        { name: "Orange" },
        { name: "Apple" },
    ]);
    pyEnv["mail.message"].create([
        {
            body: "Orange",
            res_id: channeId1,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Apple",
            res_id: channelId2,
            message_type: "comment",
            model: "discuss.channel",
        },
    ]);
    onRpcBefore("/discuss/channel/messages", () => expect.step("fetch_messages"));
    setupChatHub({ folded: [channeId1, channelId2] });
    await start();
    await contains(".o-mail-ChatBubble[name='Orange']");
    expect.verifySteps([]);
    await click(".o-mail-ChatBubble[name='Orange']");
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-Message-content", { text: "Orange" });
    await contains(".o-mail-Message-content", { count: 0, text: "Apple" });
    expect.verifySteps(["fetch_messages"]); // from "Orange" becoming open
});

test("More than 7 actually folded chat windows shows a 'hidden' chat bubble menu", async () => {
    const pyEnv = await startServer();
    const channelIds = [];
    for (let i = 1; i <= 8; i++) {
        channelIds.push(pyEnv["discuss.channel"].create({ name: String(i) }));
    }
    setupChatHub({ folded: channelIds.reverse() });
    await start();
    // Can make chat from hidden menu
    await hover(".o-mail-ChatHub-hiddenBtn");
    await click(".o-mail-ChatHub-hiddenItem");
    await leave(); // FIXME: hover is persistent otherwise
    await contains(".o-mail-ChatHub-hiddenItem", { count: 0 });
    await contains(".o-mail-ChatHub-hiddenBtn", { count: 0 });
    await contains(".o-mail-ChatWindow");
    await click(".o-mail-ChatWindow-header [title='Fold']");
    // Can open hidden chat from messaging menu
    await click("i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "2" });
    await contains(".o-mail-ChatHub-hiddenItem", { count: 0 });
    await contains(".o-mail-ChatHub-hiddenBtn", { count: 0 });
    await contains(".o-mail-ChatWindow");
    await click(".o-mail-ChatWindow-header [title='Fold']");
    // Can close chat from hidden menu.
    await hover(".o-mail-ChatHub-hiddenBtn");
    await hover(".o-mail-ChatHub-hiddenItem");
    await click(".o-mail-ChatHub-hiddenClose");
    await contains(".o-mail-ChatHub-hiddenItem", { count: 0 });
    await contains(".o-mail-ChatHub-hiddenBtn", { count: 0 });
    await contains(".o-mail-ChatWindow", { count: 0 });
});

test("Can close all chat windows at once", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create(
        Array(20)
            .keys()
            .map((i) => ({ name: String(i) }))
    );
    setupChatHub({ folded: channelIds.reverse() });
    await start();
    await contains(".o-mail-ChatBubble", { count: 8 }); // max reached
    await contains(".o-mail-ChatBubble", { text: "+13" });
    await hover(".o-mail-ChatHub-hiddenBtn");
    await click("button[title='Chat Options']");
    await click(".o-dropdown-item", { text: "Close all conversations" });
    await contains(".o-mail-ChatBubble", { count: 0 });
    assertChatHub({});
});

test("Don't show chat hub in discuss app", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create(
        range(0, 20).map((i) => ({ name: String(i) }))
    );
    setupChatHub({ folded: channelIds.reverse() });
    await start();
    await contains(".o-mail-ChatBubble", { count: 8 }); // max reached
    await contains(".o-mail-ChatBubble", { text: "+13" });
    await openDiscuss();
    await contains(".o-mail-ChatBubble", { count: 0 });
});

test("Don't show chat hub in discuss app on mobile", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    setupChatHub({ folded: [channelId] });
    await start();
    await contains(".o-mail-ChatBubble");
    await openDiscuss();
    await contains(".o-mail-ChatBubble", { count: 0 });
});

test("Can compact chat hub", async () => {
    // allows to temporarily reduce footprint of chat windows on UI
    const pyEnv = await startServer();
    const channelIds = [];
    for (let i = 1; i <= 20; i++) {
        channelIds.push(pyEnv["discuss.channel"].create({ name: String(i) }));
    }
    setupChatHub({ folded: channelIds.reverse() });
    await start();
    await contains(".o-mail-ChatBubble", { count: 8 }); // max reached
    await contains(".o-mail-ChatBubble", { text: "+13" });
    await hover(".o-mail-ChatHub-hiddenBtn");
    await click("button[title='Chat Options']");
    await click(".o-dropdown-item", { text: "Hide all conversations" });
    await contains(".o-mail-ChatBubble i.fa.fa-comments");
    await click(".o-mail-ChatBubble i.fa.fa-comments");
    await contains(".o-mail-ChatBubble", { count: 8 });
    // alternative compact: click hidden button
    await click(".o-mail-ChatBubble", { text: "+13" });
    await contains(".o-mail-ChatBubble i.fa.fa-comments");
});

test("Compact chat hub is crosstab synced", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([{ name: "ch-1" }, { name: "ch-2" }]);
    setupChatHub({ folded: channelIds });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await contains(".o-mail-ChatBubble", { count: 2, target: env1 });
    await contains(".o-mail-ChatBubble", { count: 2, target: env2 });
    await hover(".o-mail-ChatBubble:eq(0)", { target: env1 });
    await click("button[title='Chat Options']", { target: env1 });
    await click(".o-dropdown-item", { text: "Hide all conversations", target: env1 });
    await contains(".o-mail-ChatBubble .fa-comments", { target: env1 });
    await contains(".o-mail-ChatBubble .fa-comments", { target: env2 });
});

test("Compacted chat hub shows badge with amount of hidden chats with important messages", async () => {
    const pyEnv = await startServer();
    const channelIds = [];
    for (let i = 1; i <= 20; i++) {
        const partner_id = pyEnv["res.partner"].create({ name: `partner_${i}` });
        const chatId = pyEnv["discuss.channel"].create({
            name: String(i),
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id }),
            ],
            channel_type: "chat",
        });
        channelIds.push(chatId);
        if (i < 10) {
            pyEnv["mail.message"].create({
                body: "Hello!",
                model: "discuss.channel",
                author_id: partner_id,
                res_id: chatId,
            });
        }
    }
    setupChatHub({ folded: channelIds });
    await start();
    await contains(".o-mail-ChatBubble", { count: 8 }); // max reached
    await contains(".o-mail-ChatBubble", { text: "+13" });
    await click(".o-mail-ChatHub-hiddenBtn");
    await contains(".o-mail-ChatBubble i.fa.fa-comments");
    await contains(".o-mail-ChatBubble .o-discuss-badge", { text: "9" });
});

test("Show IM status", async () => {
    const pyEnv = await startServer();
    const demoId = pyEnv["res.partner"].create({ name: "Demo User", im_status: "online" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: demoId }),
        ],
        channel_type: "chat",
    });
    setupChatHub({ folded: [channelId] });
    await start();
    await contains(".o-mail-ChatBubble .fa-circle.text-success[aria-label='User is online']");
});

test("Attachment-only message preview shows file name", async () => {
    const pyEnv = await startServer();
    const [partner1, partner2, partner3] = pyEnv["res.partner"].create([
        { name: "Partner1" },
        { name: "Partner2" },
        { name: "Partner3" },
    ]);
    const [channel1, channel2, channel3] = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partner1 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partner2 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partner3 }),
            ],
            channel_type: "chat",
        },
    ]);
    pyEnv["mail.message"].create([
        {
            attachment_ids: [
                Command.create({
                    mimetype: "application/pdf",
                    name: "File.pdf",
                    res_id: channel1,
                    res_model: "discuss.channel",
                }),
            ],
            author_id: partner1,
            body: "",
            model: "discuss.channel",
            res_id: channel1,
        },
        {
            attachment_ids: [
                Command.create({
                    mimetype: "image/jpeg",
                    name: "Image.jpeg",
                    res_id: channel2,
                    res_model: "discuss.channel",
                }),
                Command.create({
                    mimetype: "application/pdf",
                    name: "File.pdf",
                    res_id: channel2,
                    res_model: "discuss.channel",
                }),
            ],
            author_id: partner2,
            body: "",
            model: "discuss.channel",
            res_id: channel2,
        },
        {
            attachment_ids: [
                Command.create({
                    mimetype: "application/pdf",
                    name: "File.pdf",
                    res_id: channel3,
                    res_model: "discuss.channel",
                }),
                Command.create({
                    mimetype: "image/jpeg",
                    name: "Image.jpeg",
                    res_id: channel3,
                    res_model: "discuss.channel",
                }),
                Command.create({
                    mimetype: "video/mp4",
                    name: "Video.mp4",
                    res_id: channel3,
                    res_model: "discuss.channel",
                }),
            ],
            author_id: partner3,
            body: "",
            model: "discuss.channel",
            res_id: channel3,
        },
    ]);
    setupChatHub({ folded: [channel1, channel2, channel3] });
    await start();
    await contains(".o-mail-ChatBubble[name='Partner1']");
    await hover(".o-mail-ChatBubble[name='Partner1']");
    await contains(".o-mail-ChatBubble-preview", { text: "Partner1File.pdf" });
    await contains(".o-mail-ChatBubble[name='Partner2']");
    await hover(".o-mail-ChatBubble[name='Partner2']");
    await contains(".o-mail-ChatBubble-preview", { text: "Partner2Image.jpeg and File.pdf" });
    await contains(".o-mail-ChatBubble[name='Partner3']");
    await hover(".o-mail-ChatBubble[name='Partner3']");
    await contains(".o-mail-ChatBubble-preview", {
        text: "Partner3File.pdf and 2 other attachments",
    });
});

test("Open chat window from messaging menu with chat hub compact", async () => {
    const pyEnv = await startServer();
    const johnId = pyEnv["res.users"].create({ name: "John" });
    const johnPartnerId = pyEnv["res.partner"].create({ user_ids: [johnId], name: "John" });
    const chatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: johnPartnerId }),
        ],
        channel_type: "chat",
    });
    setupChatHub({ folded: [chatId] });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button[title='Chat Options']");
    await click(".o-dropdown-item", { text: "Hide all conversations" });
    await contains(".o-mail-ChatHub-compact");
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "John" });
    await contains(".o-mail-ChatWindow", { text: "John" });
    await triggerEvents(".o-mail-Composer-input", ["blur", "focusout"]); // FIXME: click fold doesn't focusout/blur the composer, thus marks as read
    await click(".o-mail-ChatWindow-header [title='Fold']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await withUser(johnId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello Mitchel!", message_type: "comment" },
            thread_id: chatId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatHub-compact", { text: "1" });
    await contains(".o-mail-ChatWindow", { count: 0 });
});

test("Open chat window from command palette with chat hub compact", async () => {
    const pyEnv = await startServer();
    const johnId = pyEnv["res.users"].create({ name: "John" });
    const johnPartnerId = pyEnv["res.partner"].create({ user_ids: [johnId], name: "John" });
    const chatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: johnPartnerId }),
        ],
        channel_type: "chat",
    });
    setupChatHub({ folded: [chatId] });
    await start();
    await click("button[title='Chat Options']");
    await click(".o-dropdown-item", { text: "Hide all conversations" });
    await contains(".o-mail-ChatHub-compact");
    await triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    await click(".o-mail-DiscussCommand", { text: "John" });
    await contains(".o-mail-ChatWindow", { text: "John" });
});
