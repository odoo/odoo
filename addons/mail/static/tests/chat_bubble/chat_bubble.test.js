import { describe, expect, test } from "@odoo/hoot";
import {
    advanceTime,
    freezeTime,
    leave,
    queryOne,
    runAllTimers,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { Command, serverState, withUser } from "@web/../tests/web_test_helpers";
import {
    assertChatHub,
    click,
    defineMailModels,
    focus,
    hover,
    insertText,
    listenStoreFetch,
    openDiscuss,
    openFormView,
    openMessagingMenu,
    setupChatHub,
    start,
    startServer,
    triggerEvents,
    triggerHotkey,
    waitStoreFetch,
    MENU_ACTIVE_IDS,
} from "../mail_test_helpers";
import { BOUNCE_DURATION } from "@mail/core/common/chat_bubble";

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
    await waitFor(".o-mail-ChatBubble:count(2)");
    await click(".o-mail-ChatBubble", { count: 2 });
    await waitFor(".o-mail-ChatBubble:count(1)");
    await waitFor(".o-mail-ChatWindow:count(1)");
});

test.tags("focus required");
test("No duplicated chat bubbles", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    // Make bubble of "John" chat
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    await waitFor(".o_command_name:count(2)");
    await waitFor(".o_command:eq(0):text(John):count(1)");
    await waitFor(".o_command:eq(1):text(Mitchell Admin):count(1)");
    await insertText(".o_command_palette_search input[placeholder='Search conversations']", "John");
    await waitFor(".o_command_name:count(2)");
    await waitFor(".o_command:eq(0):text(John):count(1)");
    await waitFor(".o_command:eq(1):has(:text(Create Channel)):count(1)");
    await click(".o_command_name:text('John')");
    await waitFor(".o-mail-ChatWindow-displayName:text('John'):count(1)");
    await waitFor(
        ".o-mail-ChatWindow .o-mail-Thread-empty:has(:text('This is the start of your direct chat with John')):count(1)"
    );
    await click("button[title='Fold']");
    await waitFor(".o-mail-ChatBubble[name='John']:count(1)");
    // Make bubble of "John" chat again
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    await waitFor(".o_command_name:count(2)");
    await insertText(".o_command_palette_search input[placeholder='Search conversations']", "John");
    await waitFor(".o_command_name:count(2)");
    await waitFor(".o_command:eq(0):text(John):count(1)");
    await waitFor(".o_command:eq(1):has(:text(Create Channel)):count(1)");
    await click(".o_command_name:text('John')");
    await waitForNone(".o-mail-ChatBubble[name='John']");
    await waitFor(".o-mail-ChatWindow .o-mail-ChatWindow-header:has(:text('John')):count(1)");
    await click(".o-mail-ChatWindow-header [title='Fold']");
    // Make again from click messaging menu item
    await openMessagingMenu();
    await click(".o-mail-NotificationItem");
    await waitForNone(".o-mail-ChatBubble[name='John']");
    await waitFor(".o-mail-ChatWindow .o-mail-ChatWindow-header:has(:text('John')):count(1)");
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
        await waitFor(`.o-mail-ChatBubble[name='${String(i)}']:count(1)`);
    }
    await waitForNone(".o-mail-ChatBubble[name='1']");
    await waitFor(".o-mail-ChatHub-hiddenBtn:text('+1'):count(1)");
    await hover(".o-mail-ChatHub-hiddenBtn");
    await waitFor(".o-mail-ChatHub-hiddenItem[name='1']:count(1)");
    await waitForNone(".o-mail-ChatWindow");
    await click(".o-mail-ChatHub-hiddenItem");
    await waitFor(".o-mail-ChatWindow:count(1)");
    await waitForNone(".o-mail-ChatHub-hiddenBtn");
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
    await waitFor(":nth-child(1 of .o-mail-ChatBubble)[name='7']");
    await waitFor(":nth-child(2 of .o-mail-ChatBubble)[name='6']");
    await waitFor(":nth-child(3 of .o-mail-ChatBubble)[name='5']");
    await waitFor(":nth-child(4 of .o-mail-ChatBubble)[name='4']");
    await waitFor(":nth-child(5 of .o-mail-ChatBubble)[name='3']");
    await waitFor(":nth-child(6 of .o-mail-ChatBubble)[name='2']");
    await waitFor(":nth-child(7 of .o-mail-ChatBubble)[name='1']");
    await waitForNone(".o-mail-ChatBubble[name='Demo']");
    await waitForNone(".o-mail-ChatWindow");
    await click(".o-mail-ChatBubble[name='3']");
    await waitFor(".o-mail-ChatWindow-displayName:text('3'):count(1)");
    await waitFor(":nth-child(7 of .o-mail-ChatBubble)[name='Demo']");
    await click(".o-mail-ChatWindow-header [title='Fold']");
    await waitForNone(".o-mail-ChatBubble[name='Demo']");
    await click(".o-mail-ChatBubble[name='4']");
    await waitFor(":nth-child(1 of .o-mail-ChatBubble)[name='3']");
    await waitFor(":nth-child(2 of .o-mail-ChatBubble)[name='7']");
    await waitFor(":nth-child(3 of .o-mail-ChatBubble)[name='6']");
    await waitFor(":nth-child(7 of .o-mail-ChatBubble)[name='Demo']");
    await click(".o-mail-ChatWindow-header [title='Fold']");
    await waitForNone(".o-mail-ChatWindow");
    // no reorder on receiving new message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "test", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await hover(".o-mail-ChatHub-hiddenBtn");
    await waitFor(".o-mail-ChatHub-hiddenItem[name='Demo']:count(1)");
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
    await waitFor(".o-mail-ChatBubble[name='Marc'].o-active:count(1)");
    await waitFor(".o-mail-ChatBubble-preview:text('Marc Hello!'):count(1)");
    await leave();
    await waitForNone(".o-mail-ChatBubble-preview");
    await waitFor(".o-mail-ChatBubble[name='Marc']:not(.o-active):count(1)");
    await hover(".o-mail-ChatBubble[name='Demo']");
    await waitFor(
        ".o-mail-ChatBubble-preview:text('Demo This is the start of your conversation'):count(1)"
    );
    await leave();
    rpc("/mail/message/post", {
        post_data: { body: "Hi", message_type: "comment" },
        thread_id: demoChannelId,
        thread_model: "discuss.channel",
    });
    await hover(".o-mail-ChatBubble[name='Demo']");
    await waitFor(".o-mail-ChatBubble-preview:text('Demo You: Hi'):count(1)");
});

test("Escape closes a chat bubble preview containing a focused link", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: '<a href="https://odoo.com/">https://odoo.com</a>',
        model: "discuss.channel",
        res_id: channelId,
    });
    setupChatHub({ folded: [channelId] });
    await start();
    await hover(".o-mail-ChatBubble[name='General']");
    await waitFor(".o-mail-ChatBubble-preview:count(1)");
    // Do not focus the anchor automatically, as doing so would show an empty preview for long messages with trailing link
    await focus('.o-mail-ChatBubble-preview a[href="https://odoo.com/"]:not(:focus)');
    await triggerHotkey("Escape");
    await waitForNone(".o-mail-ChatBubble-preview");
});

test("Hover on chat bubble shows message preview along with message seen indicator", async () => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({ name: "Marc" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
        ],
        channel_type: "chat",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello there!!!",
        model: "discuss.channel",
        res_id: channelId,
    });
    const memberIds = pyEnv["discuss.channel.member"].search([["channel_id", "=", channelId]]);
    pyEnv["discuss.channel.member"].write(memberIds, { seen_message_id: false });
    const [memberId_1] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", partnerId_1],
    ]);
    pyEnv["discuss.channel.member"].write([memberId_1], {
        seen_message_id: messageId,
    });
    setupChatHub({ folded: [channelId] });
    await start();
    await hover(".o-mail-ChatBubble[name='Marc']");
    await waitFor(".o-mail-ChatBubble-preview:text('Marc You: Hello there!!!'):count(1)");
    await waitFor(".o-mail-MessageSeenIndicator[title='Seen by Marc']:count(1)");
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
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await click(".o-mail-NotificationItem");
    await click(".o-mail-ChatWindow [title='Fold']");
    await hover(".o-mail-ChatBubble");
    await waitFor(
        ".o-mail-ChatBubble-preview:has(:text('md@oilcompany.fr: Some email message')):count(1)"
    );
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
    const tab2 = await start({ asTab: true, waitUntilSubscribe: false });
    await waitFor(`${tab1.selector} .o-mail-ChatBubble:count(1)`);
    await waitFor(`${tab2.selector} .o-mail-ChatBubble:count(1)`);
    await runAllTimers(); // Wait for bus service to fully load
    await click(`${tab1.selector} .o-mail-ChatBubble[name='Marc']`);
    await waitFor(`${tab2.selector} .o-mail-ChatWindow:count(1)`); // open sync
    await click(`${tab2.selector} .o-mail-ChatWindow-header [title='Fold']`);
    await waitForNone(`${tab1.selector} .o-mail-ChatWindow`); // fold sync
    await click(`${tab1.selector} .o-mail-ChatBubble[name='Marc'] .o-mail-ChatBubble-close`);
    await waitForNone(`${tab2.selector} .o-mail-ChatBubble[name='Marc']`); // close sync
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
    listenStoreFetch("/discuss/channel/messages");
    setupChatHub({ folded: [channeId1, channelId2] });
    await start();
    await waitFor(".o-mail-ChatBubble[name='Orange']:count(1)");
    await waitStoreFetch();
    await click(".o-mail-ChatBubble[name='Orange']");
    await waitFor(".o-mail-ChatWindow:count(1)");
    await waitFor(".o-mail-Message-content:text('Orange'):count(1)");
    await waitForNone(".o-mail-Message-content:text('Apple')");
    await waitStoreFetch("/discuss/channel/messages"); // from "Orange" becoming open
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
    await waitForNone(".o-mail-ChatHub-hiddenItem");
    await waitForNone(".o-mail-ChatHub-hiddenBtn");
    await waitFor(".o-mail-ChatWindow:count(1)");
    await click(".o-mail-ChatWindow-header [title='Fold']");
    // Can open hidden channels from messaging menu
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await click(".o-mail-NotificationItem-name:text('2')");
    await waitForNone(".o-mail-ChatHub-hiddenItem");
    await waitForNone(".o-mail-ChatHub-hiddenBtn");
    await waitFor(".o-mail-ChatWindow:count(1)");
    await click(".o-mail-ChatWindow-header [title='Fold']");
    // Can close channels from hidden menu.
    await hover(".o-mail-ChatHub-hiddenBtn");
    await hover(".o-mail-ChatHub-hiddenItem");
    await click(".o-mail-ChatHub-hiddenClose");
    await waitForNone(".o-mail-ChatHub-hiddenItem");
    await waitForNone(".o-mail-ChatHub-hiddenBtn");
    await waitForNone(".o-mail-ChatWindow");
});

test("Can close all chat windows at once", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create(range(20).map((i) => ({ name: String(i) })));
    setupChatHub({ folded: channelIds.reverse() });
    await start();
    await waitFor(".o-mail-ChatBubble:count(8)"); // max reached
    await waitFor(".o-mail-ChatBubble:text('+13'):count(1)");
    await hover(".o-mail-ChatHub-hiddenBtn");
    await click("button[title='Chat Options']");
    await click(".o-dropdown-item:text('Close all conversations')");
    await waitForNone(".o-mail-ChatBubble");
    assertChatHub({});
});

test("Don't show chat hub in discuss app", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create(range(20).map((i) => ({ name: String(i) })));
    setupChatHub({ folded: channelIds.reverse() });
    await start();
    await waitFor(".o-mail-ChatBubble:count(8)"); // max reached
    await waitFor(".o-mail-ChatBubble:text('+13'):count(1)");
    await openDiscuss();
    await waitForNone(".o-mail-ChatBubble");
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
    await waitFor(".o-mail-ChatBubble:count(8)"); // max reached
    await waitFor(".o-mail-ChatBubble:text('+13'):count(1)");
    await hover(".o-mail-ChatHub-hiddenBtn");
    await click("button[title='Chat Options']");
    await click(".o-dropdown-item:text('Hide all conversations')");
    await waitFor(".o-mail-ChatBubble i.oi[data-icon='forum']:count(1)");
    await click(".o-mail-ChatBubble i.oi[data-icon='forum']");
    await waitFor(".o-mail-ChatBubble:count(8)");
    // alternative compact: click hidden button
    await click(".o-mail-ChatBubble:text('+13')");
    await waitFor(".o-mail-ChatBubble i.oi[data-icon='forum']:count(1)");
    // don't show compact button in discuss app
    await openDiscuss();
    await waitFor(".o-mail-Discuss[data-active]:count(1)");
    await waitForNone(".o-mail-ChatBubble i.oi[data-icon='forum']");
});

test("Compact chat hub is crosstab synced", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([{ name: "ch-1" }, { name: "ch-2" }]);
    setupChatHub({ folded: channelIds });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true, waitUntilSubscribe: false });
    await waitFor(`${env1.selector} .o-mail-ChatBubble:count(2)`);
    await waitFor(`${env2.selector} .o-mail-ChatBubble:count(2)`);
    await hover(`${env1.selector} .o-mail-ChatBubble:eq(0)`);
    await click(`${env1.selector} button[title='Chat Options']`);
    await click(`${env1.selector} .o-dropdown-item:text('Hide all conversations')`);
    await waitFor(`${env1.selector} .o-mail-ChatBubble .oi[data-icon='forum']:count(1)`);
    await waitFor(`${env2.selector} .o-mail-ChatBubble .oi[data-icon='forum']:count(1)`);
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
    await waitFor(".o-mail-ChatBubble:count(8)"); // max reached
    await waitFor(".o-mail-ChatBubble .o-mail-ChatHub-hiddenBtnIcon:text('+13'):count(1)");
    await click(".o-mail-ChatHub-hiddenBtn");
    await waitFor(".o-mail-ChatBubble i.oi[data-icon='forum']:count(1)");
    await waitFor(".o-mail-ChatBubble .o-discuss-badge:text('9'):count(1)");
});

test("Show IM status", async () => {
    const pyEnv = await startServer();
    const demoId = pyEnv["res.partner"].create({ name: "Demo User" });
    pyEnv["res.users"].create({ partner_id: demoId, im_status: "online" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: demoId }),
        ],
        channel_type: "chat",
    });
    setupChatHub({ folded: [channelId] });
    await start();
    await waitFor(
        ".o-mail-ChatBubble [data-icon='circle'].oi-filled.text-success[aria-label='User is online']:count(1)"
    );
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
    await waitFor(".o-mail-ChatBubble[name='Partner1']:count(1)");
    await hover(".o-mail-ChatBubble[name='Partner1']");
    await waitFor(".o-mail-ChatBubble-preview:text('Partner1 File.pdf'):count(1)");
    await waitFor(".o-mail-ChatBubble[name='Partner2']:count(1)");
    await hover(".o-mail-ChatBubble[name='Partner2']");
    await waitFor(".o-mail-ChatBubble-preview:text('Partner2 Image.jpeg and File.pdf'):count(1)");
    await waitFor(".o-mail-ChatBubble[name='Partner3']:count(1)");
    await hover(".o-mail-ChatBubble[name='Partner3']");
    await waitFor(
        ".o-mail-ChatBubble-preview:text('Partner3 File.pdf and 2 other attachments'):count(1)"
    );
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
    listenStoreFetch("/discuss/channel/messages");
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button[title='Chat Options']");
    await click(".o-dropdown-item:text('Hide all conversations')");
    await waitFor(".o-mail-ChatHub-compact:count(1)");
    await openMessagingMenu();
    await click(".o-mail-NotificationItem-name:text('John')");
    await waitStoreFetch("/discuss/channel/messages"); // ensure messages are loaded before doing message post
    await waitFor(".o-mail-ChatWindow-displayName:text('John'):count(1)");
    await click(".o-mail-ChatWindow-header [title='Fold']");
    await waitForNone(".o-mail-ChatWindow");
    await withUser(johnId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello Mitchel!", message_type: "comment" },
            thread_id: chatId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-ChatHub-compact:text('1'):count(1)");
    await waitForNone(".o-mail-ChatWindow");
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
    await click(".o-dropdown-item:text('Hide all conversations')");
    await waitFor(".o-mail-ChatHub-compact:count(1)");
    await triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    await click(".o-mail-DiscussCommand:text('John')");
    await waitFor(".o-mail-ChatWindow-displayName:text('John'):count(1)");
});

test("Close chat window from bubble while bubble preview is displayed", async () => {
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
    await hover(".o-mail-ChatBubble[name='John']");
    await click(`.o-mail-ChatBubble[name='John'] .o-mail-ChatBubble-close`);
    await waitForNone(`.o-mail-ChatBubble[name='John']`);
});

test("Chat bubble bounces on new important messages only, until they stop coming", async () => {
    const pyEnv = await startServer();
    const johnUserId = pyEnv["res.users"].create({ name: "John" });
    const johnPartnerId = pyEnv["res.partner"].create({ user_ids: [johnUserId], name: "John" });
    const chatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                message_unread_counter: 1,
                new_message_separator: 0,
                partner_id: serverState.partnerId,
                seen_message_id: false,
            }),
            Command.create({ partner_id: johnPartnerId }),
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        author_id: johnPartnerId,
        body: "Hello!",
        message_type: "comment",
        model: "discuss.channel",
        res_id: chatId,
    });
    const johnPosts = (body) =>
        withUser(johnUserId, () =>
            rpc("/mail/message/post", {
                post_data: { body, message_type: "comment" },
                thread_id: chatId,
                thread_model: "discuss.channel",
            })
        );
    // Animations are disabled in tests: simulate the end of a bounce iteration.
    const bounce = () => triggerEvents(".o-mail-ChatBubble[name='John']", ["animationiteration"]);
    setupChatHub({ folded: [chatId] });
    await start();
    freezeTime(); // to make bouncing checks unaffected by CPU load
    // Messages that were already unread on mount do not trigger a bounce.
    await waitFor(".o-mail-ChatBubble[name='John'] .o-mail-ChatBubble-counter:text('1'):count(1)");
    await waitForNone(".o-mail-ChatBubble.o-bouncing");
    await johnPosts("Anyone here?");
    await waitFor(".o-mail-ChatBubble.o-bouncing:count(1)");
    // A restarted animation would momentarily drop the class to force a reflow.
    let animationInterrupted = false;
    const observer = new MutationObserver((records) => {
        animationInterrupted ||= records.some(
            ({ target }) => !target.classList.contains("o-bouncing")
        );
    });
    observer.observe(queryOne(".o-mail-ChatBubble[name='John']"), { attributeFilter: ["class"] });
    // Half-way through the bounce, another message comes in.
    await advanceTime(BOUNCE_DURATION / 2);
    await bounce();
    await johnPosts("Are you there?");
    await waitFor(".o-mail-ChatBubble-counter:text('3'):count(1)");
    // First deadline passed: still bouncing, never interrupted.
    await advanceTime(BOUNCE_DURATION / 2);
    await bounce();
    await waitFor(".o-mail-ChatBubble.o-bouncing:count(1)");
    expect(animationInterrupted).toBe(false);
    observer.disconnect();
    // It only stops a full bounce duration after the newest message.
    await advanceTime(BOUNCE_DURATION / 2 - 1);
    await bounce();
    await waitFor(".o-mail-ChatBubble.o-bouncing:count(1)");
    await advanceTime(1);
    await bounce();
    await waitForNone(".o-mail-ChatBubble.o-bouncing");
});
