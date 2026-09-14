// @ts-check
import { registerImStatusDecoration } from "@mail/core/common/presence_status";
import { describe, expect, test } from "@odoo/hoot";
import { leave, runAllTimers } from "@odoo/hoot-dom";
import { Command, serverState, withUser } from "@web/../tests/web_test_helpers";
import { rpc } from "@web/core/network";
import { range } from "@web/core/utils/format/numbers";

import { createChannelMessages, createChatWith } from "../mail_scenarios.js";
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
    setupChatHub,
    start,
    startServer,
    triggerEvents,
    triggerHotkey,
} from "../mail_test_helpers.js";

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
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu button", { text: "New Message" });
    await contains(".o_command_name", { count: 5 });
    await insertText("input[placeholder='Search a conversation']", "John");
    await contains(".o_command_name", { count: 3 });
    await click(".o_command_name", { text: "John" });
    await contains(".o-mail-ChatWindow", { text: "John" });
    await contains(".o-mail-ChatWindow", {
        text: "This is the start of your direct chat with John",
    });
    await click("button[title='Fold']");
    await contains(".o-mail-ChatBubble[name='John']");
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu button", { text: "New Message" });
    await contains(".o_command_name", { count: 5 });
    await insertText("input[placeholder='Search a conversation']", "John");
    await contains(".o_command_name", { count: 3 });
    await click(".o_command_name", { text: "John" });
    await contains(".o-mail-ChatBubble[name='John']", { count: 0 });
    await contains(".o-mail-ChatWindow", { text: "John" });
    await click(".o-mail-ChatWindow-header [title='Fold']");
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
    const { channelId } = createChatWith(pyEnv, { partnerId });
    const channelIds = [channelId];
    for (let i = 1; i <= 7; i++) {
        channelIds.push(pyEnv["discuss.channel"].create({ name: String(i) }));
    }
    setupChatHub({ folded: channelIds.reverse() });
    await start();
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
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "test", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        }),
    );
    await hover(".o-mail-ChatHub-hiddenBtn");
    await contains(".o-mail-ChatHub-hiddenItem[name='Demo']");
});

test("Hover on chat bubble shows chat name + last message preview", async () => {
    const pyEnv = await startServer();
    const { channelId: marcChannelId, partnerId: marcPartnerId } = createChatWith(
        pyEnv,
        {
            name: "Marc",
            user: false,
        },
    );
    createChannelMessages(pyEnv, marcChannelId, [
        { body: "Hello!", author_id: marcPartnerId },
    ]);
    const { channelId: demoChannelId } = createChatWith(pyEnv, {
        name: "Demo",
        user: false,
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
    await rpc("/mail/message/post", {
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
    await contains(".o-mail-ChatBubble-preview", {
        text: "md@oilcompany.fr: Some email message",
    });
});

test("chat bubbles are synced between tabs", async () => {
    const pyEnv = await startServer();
    const { channelId } = createChatWith(pyEnv, { name: "Marc", user: false });
    setupChatHub({ folded: [channelId] });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    await contains(`${tab1.selector} .o-mail-ChatBubble`);
    await contains(`${tab2.selector} .o-mail-ChatBubble`);
    await runAllTimers();
    await click(`${tab1.selector} .o-mail-ChatBubble[name='Marc']`);
    await contains(`${tab2.selector} .o-mail-ChatWindow`);
    await click(`${tab2.selector} .o-mail-ChatWindow-header [title='Fold']`);
    await contains(`${tab1.selector} .o-mail-ChatWindow`, { count: 0 });
    await click(
        `${tab1.selector} .o-mail-ChatBubble[name='Marc'] .o-mail-ChatBubble-close`,
    );
    await contains(`${tab2.selector} .o-mail-ChatBubble[name='Marc']`, { count: 0 });
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
    expect.verifySteps(["fetch_messages"]);
});

test("More than 7 actually folded chat windows shows a 'hidden' chat bubble menu", async () => {
    const pyEnv = await startServer();
    const channelIds = [];
    for (let i = 1; i <= 8; i++) {
        channelIds.push(pyEnv["discuss.channel"].create({ name: String(i) }));
    }
    setupChatHub({ folded: channelIds.reverse() });
    await start();
    await hover(".o-mail-ChatHub-hiddenBtn");
    await click(".o-mail-ChatHub-hiddenItem");
    await leave();
    await contains(".o-mail-ChatHub-hiddenItem", { count: 0 });
    await contains(".o-mail-ChatHub-hiddenBtn", { count: 0 });
    await contains(".o-mail-ChatWindow");
    await click(".o-mail-ChatWindow-header [title='Fold']");
    await click("i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "2" });
    await contains(".o-mail-ChatHub-hiddenItem", { count: 0 });
    await contains(".o-mail-ChatHub-hiddenBtn", { count: 0 });
    await contains(".o-mail-ChatWindow");
    await click(".o-mail-ChatWindow-header [title='Fold']");
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
            .map((i) => ({ name: String(i) })),
    );
    setupChatHub({ folded: channelIds.reverse() });
    await start();
    await contains(".o-mail-ChatBubble", { count: 8 });
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
        range(0, 20).map((i) => ({ name: String(i) })),
    );
    setupChatHub({ folded: channelIds.reverse() });
    await start();
    await contains(".o-mail-ChatBubble", { count: 8 });
    await contains(".o-mail-ChatBubble", { text: "+13" });
    await openDiscuss();
    await contains(".o-mail-ChatBubble", { count: 0 });
});

test("Can compact chat hub", async () => {
    const pyEnv = await startServer();
    const channelIds = [];
    for (let i = 1; i <= 20; i++) {
        channelIds.push(pyEnv["discuss.channel"].create({ name: String(i) }));
    }
    setupChatHub({ folded: channelIds.reverse() });
    await start();
    await contains(".o-mail-ChatBubble", { count: 8 });
    await contains(".o-mail-ChatBubble", { text: "+13" });
    await hover(".o-mail-ChatHub-hiddenBtn");
    await click("button[title='Chat Options']");
    await click(".o-dropdown-item", { text: "Hide all conversations" });
    await contains(".o-mail-ChatBubble i.fa-solid.fa-comments");
    await click(".o-mail-ChatBubble i.fa-solid.fa-comments");
    await contains(".o-mail-ChatBubble", { count: 8 });
    await click(".o-mail-ChatBubble", { text: "+13" });
    await contains(".o-mail-ChatBubble i.fa-solid.fa-comments");
    await openDiscuss();
    await contains(".o-mail-Discuss[data-active]");
    await contains(".o-mail-ChatBubble i.fa-solid.fa-comments", { count: 0 });
});

test("Compact chat hub is crosstab synced", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([
        { name: "ch-1" },
        { name: "ch-2" },
    ]);
    setupChatHub({ folded: channelIds });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await contains(`${env1.selector} .o-mail-ChatBubble`, { count: 2 });
    await contains(`${env2.selector} .o-mail-ChatBubble`, { count: 2 });
    await hover(`${env1.selector} .o-mail-ChatBubble:eq(0)`);
    await click(`${env1.selector} button[title='Chat Options']`);
    await click(`${env1.selector} .o-dropdown-item`, {
        text: "Hide all conversations",
    });
    await contains(`${env1.selector} .o-mail-ChatBubble .fa-comments`);
    await contains(`${env2.selector} .o-mail-ChatBubble .fa-comments`);
});

test("Compacted chat hub shows badge with amount of hidden chats with important messages", async () => {
    const pyEnv = await startServer();
    const channelIds = [];
    for (let i = 1; i <= 20; i++) {
        const { channelId: chatId, partnerId } = createChatWith(pyEnv, {
            name: `partner_${i}`,
            user: false,
            channel: { name: String(i) },
        });
        channelIds.push(chatId);
        if (i < 10) {
            createChannelMessages(pyEnv, chatId, [
                { body: "Hello!", author_id: partnerId },
            ]);
        }
    }
    setupChatHub({ folded: channelIds });
    await start();
    await contains(".o-mail-ChatBubble", { count: 8 });
    await contains(".o-mail-ChatBubble", { text: "+13" });
    await contains(".o-mail-ChatHub-hiddenBtn .o-mail-ChatHub-hiddenBtnCounter", {
        text: "2",
    });
    await click(".o-mail-ChatHub-hiddenBtn");
    await contains(".o-mail-ChatBubble i.fa-solid.fa-comments");
    await contains(".o-mail-ChatBubble .o-discuss-badge", { text: "9" });
});

test("Show IM status", async () => {
    const pyEnv = await startServer();
    const { channelId } = createChatWith(pyEnv, {
        name: "Demo User",
        user: false,
        partner: { im_status: "online" },
    });
    setupChatHub({ folded: [channelId] });
    await start();
    await contains(
        ".o-mail-ChatBubble .fa-circle.text-success[aria-label='User is online']",
    );
});

test("A decorated offline status hides the dot, as a plain offline one does", async () => {
    // hr_homeworking writes `home_offline` and hr_holidays `leave_offline` into
    // im_status; a comparison against the literal "offline" reads either as
    // reachable and shows the dot for someone who is not there.
    registerImStatusDecoration("testbubble_offline", "offline");
    const pyEnv = await startServer();
    const { channelId } = createChatWith(pyEnv, {
        name: "Demo User",
        user: false,
        partner: { im_status: "testbubble_offline" },
    });
    setupChatHub({ folded: [channelId] });
    await start();
    await contains(".o-mail-ChatBubble");
    await contains(".o-mail-ChatBubble-status", { count: 0 });
});

test("A decorated reachable status still shows the dot", async () => {
    registerImStatusDecoration("testbubble_online", "online");
    const pyEnv = await startServer();
    const { channelId } = createChatWith(pyEnv, {
        name: "Demo User",
        user: false,
        partner: { im_status: "testbubble_online" },
    });
    setupChatHub({ folded: [channelId] });
    await start();
    await contains(".o-mail-ChatBubble-status");
});

test("Attachment-only message preview shows file name", async () => {
    const pyEnv = await startServer();
    const [partner1, partner2, partner3] = pyEnv["res.partner"].create([
        { name: "Partner1" },
        { name: "Partner2" },
        { name: "Partner3" },
    ]);
    const { channelId: channel1 } = createChatWith(pyEnv, { partnerId: partner1 });
    const { channelId: channel2 } = createChatWith(pyEnv, { partnerId: partner2 });
    const { channelId: channel3 } = createChatWith(pyEnv, { partnerId: partner3 });
    createChannelMessages(pyEnv, channel1, [
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
        },
    ]);
    createChannelMessages(pyEnv, channel2, [
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
        },
    ]);
    createChannelMessages(pyEnv, channel3, [
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
        },
    ]);
    setupChatHub({ folded: [channel1, channel2, channel3] });
    await start();
    await contains(".o-mail-ChatBubble[name='Partner1']");
    await hover(".o-mail-ChatBubble[name='Partner1']");
    await contains(".o-mail-ChatBubble-preview", { text: "Partner1File.pdf" });
    await contains(".o-mail-ChatBubble[name='Partner2']");
    await hover(".o-mail-ChatBubble[name='Partner2']");
    await contains(".o-mail-ChatBubble-preview", {
        text: "Partner2Image.jpeg and File.pdf",
    });
    await contains(".o-mail-ChatBubble[name='Partner3']");
    await hover(".o-mail-ChatBubble[name='Partner3']");
    await contains(".o-mail-ChatBubble-preview", {
        text: "Partner3File.pdf and 2 other attachments",
    });
});

test("Open chat window from messaging menu with chat hub compact", async () => {
    const pyEnv = await startServer();
    const johnId = pyEnv["res.users"].create({ name: "John" });
    const johnPartnerId = pyEnv["res.partner"].create({
        user_ids: [johnId],
        name: "John",
    });
    const { channelId: chatId } = createChatWith(pyEnv, { partnerId: johnPartnerId });
    setupChatHub({ folded: [chatId] });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button[title='Chat Options']");
    await click(".o-dropdown-item", { text: "Hide all conversations" });
    await contains(".o-mail-ChatHub-compact");
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "John" });
    await contains(".o-mail-ChatWindow", { text: "John" });
    await triggerEvents(".o-mail-Composer-input", ["blur", "focusout"]);
    await click(".o-mail-ChatWindow-header [title='Fold']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await withUser(johnId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello Mitchel!", message_type: "comment" },
            thread_id: chatId,
            thread_model: "discuss.channel",
        }),
    );
    await contains(".o-mail-ChatHub-compact", { text: "1" });
    await contains(".o-mail-ChatWindow", { count: 0 });
});

test("Open chat window from command palette with chat hub compact", async () => {
    const pyEnv = await startServer();
    const johnId = pyEnv["res.users"].create({ name: "John" });
    const johnPartnerId = pyEnv["res.partner"].create({
        user_ids: [johnId],
        name: "John",
    });
    const { channelId: chatId } = createChatWith(pyEnv, { partnerId: johnPartnerId });
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
