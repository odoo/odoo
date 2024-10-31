import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    insertText,
    onRpcBefore,
    openDiscuss,
    scroll,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";
import { mockService, serverState, withUser } from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("reply: discard on reply button toggle", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
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
    await openDiscuss();
    await contains(".o-mail-Message");
    await click("[title='Reply']");
    await contains(".o-mail-Composer");
    await click("[title='Reply']");
    await contains(".o-mail-Composer", { count: 0 });
});

test.tags("focus required")("reply: discard on pressing escape", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartnert@odoo.com",
        name: "TestPartner",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
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
    await openDiscuss();
    await contains(".o-mail-Message");
    await click("[title='Reply']");
    await contains(".o-mail-Composer");
    // Escape on emoji picker does not stop replying
    await click(".o-mail-Composer button[aria-label='Emojis']");
    await contains(".o-EmojiPicker");
    triggerHotkey("Escape");
    await contains(".o-EmojiPicker", { count: 0 });
    await contains(".o-mail-Composer");
    // Escape on suggestion prompt does not stop replying
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestionList .o-open");
    triggerHotkey("Escape");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await contains(".o-mail-Composer");
    await click(".o-mail-Composer-input").catch(() => {});
    triggerHotkey("Escape");
    await contains(".o-mail-Composer", { count: 0 });
});

test('"reply to" composer should log note if message replied to is a note', async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        is_note: true,
        model: "res.partner",
        needaction: true,
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    onRpcBefore("/mail/message/post", (args) => {
        step("/mail/message/post");
        expect(args.post_data.message_type).toBe("comment");
        expect(args.post_data.subtype_xmlid).toBe("mail.mt_note");
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-Message");
    await click("[title='Reply']");
    await contains(".o-mail-Composer [placeholder='Log an internal note…']");
    await insertText(".o-mail-Composer-input", "Test");
    await click(".o-mail-Composer-send:enabled", { text: "Log" });
    await contains(".o-mail-Composer", { count: 0 });
    await assertSteps(["/mail/message/post"]);
});

test('"reply to" composer should send message if message replied to is not a note', async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        is_discussion: true,
        model: "res.partner",
        needaction: true,
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    onRpcBefore("/mail/message/post", (args) => {
        step("/mail/message/post");
        expect(args.post_data.message_type).toBe("comment");
        expect(args.post_data.subtype_xmlid).toBe("mail.mt_comment");
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-Message");
    await click("[title='Reply']");
    await contains(".o-mail-Composer [placeholder='Send a message to followers…']");
    await insertText(".o-mail-Composer-input", "Test");
    await click(".o-mail-Composer-send[aria-label='Send']:enabled");
    await contains(".o-mail-Composer-send", { count: 0 });
    await assertSteps(["/mail/message/post"]);
});

test("show subject of message in Inbox", async () => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        needaction: true,
        subject: "Salutations, voyageur",
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-Message", { text: "Subject: Salutations, voyageurnot empty" });
});

test("show subject of message in history", async () => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        subject: "Salutations, voyageur",
    });
    pyEnv["mail.notification"].create({
        is_read: true,
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss("mail.box_history");
    await contains(".o-mail-Message", { text: "Subject: Salutations, voyageurnot empty" });
});

test("subject should not be shown when subject is the same as the thread name", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "Salutations, voyageur" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        needaction: true,
        subject: "Salutations, voyageur",
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss("mail.box_inbox");
    await contains(".o-mail-Message");
    await contains(".o-mail-Message", {
        count: 0,
        text: "Subject: Salutations, voyageurnot empty",
    });
});

test("subject should not be shown when subject is the same as the thread name and both have the same prefix", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "Re: Salutations, voyageur" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        needaction: true,
        subject: "Re: Salutations, voyageur",
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss("mail.box_inbox");
    await contains(".o-mail-Message");
    await contains(".o-mail-Message", {
        count: 0,
        text: "Subject: Salutations, voyageurnot empty",
    });
});

test('subject should not be shown when subject differs from thread name only by the "Re:" prefix', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "Salutations, voyageur" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        needaction: true,
        subject: "Re: Salutations, voyageur",
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss("mail.box_inbox");
    await contains(".o-mail-Message");
    await contains(".o-mail-Message", {
        count: 0,
        text: "Subject: Salutations, voyageurnot empty",
    });
});

test('subject should not be shown when subject differs from thread name only by the "Fw:" and "Re:" prefix', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "Salutations, voyageur" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        needaction: true,
        subject: "Fw: Re: Salutations, voyageur",
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss("mail.box_inbox");
    await contains(".o-mail-Message");
    await contains(".o-mail-Message", {
        count: 0,
        text: "Subject: Salutations, voyageurnot empty",
    });
});

test("subject should be shown when the thread name has an extra prefix compared to subject", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "Re: Salutations, voyageur" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        needaction: true,
        subject: "Salutations, voyageur",
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss("mail.box_inbox");
    await contains(".o-mail-Message");
    await contains(".o-mail-Message", {
        count: 0,
        text: "Subject: Salutations, voyageurnot empty",
    });
});

test('subject should not be shown when subject differs from thread name only by the "fw:" prefix and both contain another common prefix', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "Re: Salutations, voyageur" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        needaction: true,
        subject: "fw: re: Salutations, voyageur",
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss("mail.box_inbox");
    await contains(".o-mail-Message");
    await contains(".o-mail-Message", {
        count: 0,
        text: "Subject: Salutations, voyageurnot empty",
    });
});

test('subject should not be shown when subject differs from thread name only by the "Re: Re:" prefix', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "Salutations, voyageur" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        needaction: true,
        subject: "Re: Re: Salutations, voyageur",
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss("mail.box_inbox");
    await contains(".o-mail-Message");
    await contains(".o-mail-Message", {
        count: 0,
        text: "Subject: Salutations, voyageurnot empty",
    });
});

test("inbox: mark all messages as read", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            body: "not empty",
            model: "discuss.channel",
            needaction: true,
            res_id: channelId,
        },
        {
            body: "not empty",
            model: "discuss.channel",
            needaction: true,
            res_id: channelId,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
        {
            mail_message_id: messageId_2,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    await start();
    await openDiscuss();
    await contains("button", { text: "Inbox", contains: [".badge", { text: "2" }] });
    await contains(".o-mail-DiscussSidebarChannel", {
        contains: [
            ["span", { text: "General" }],
            [".badge", { text: "2" }],
        ],
    });
    await contains(".o-mail-Discuss-content .o-mail-Message", { count: 2 });
    await click(".o-mail-Discuss-header button:enabled", { text: "Mark all read" });
    await contains("button", { text: "Inbox", contains: [".badge", { count: 0 }] });
    await contains(".o-mail-DiscussSidebarChannel", {
        contains: [
            ["span", { text: "General" }],
            [".badge", { count: 0 }],
        ],
    });
    await contains(".o-mail-Message", { count: 0 });
    await contains("button:disabled", { text: "Mark all read" });
});

test("inbox: mark as read should not display jump to present", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const msgIds = pyEnv["mail.message"].create(
        Array(30)
            .keys()
            .map((i) => ({
                body: "not empty".repeat(100),
                model: "discuss.channel",
                needaction: true,
                res_id: channelId,
            }))
    );
    pyEnv["mail.notification"].create(
        Array(30)
            .keys()
            .map((i) => ({
                mail_message_id: msgIds[i],
                notification_type: "inbox",
                res_partner_id: serverState.partnerId,
            }))
    );
    await start();
    await openDiscuss();
    // scroll up so that there's the "Jump to Present".
    // So that assertion of negative matches the positive assertion
    await contains(".o-mail-Message", { count: 30 });
    await scroll(".o-mail-Thread", 0);
    await contains("[title='Jump to Present']");
    await click(".o-mail-Discuss-header button:enabled", { text: "Mark all read" });
    await contains("[title='Jump to Present']", { count: 0 });
});

test("click on (non-channel/non-partner) origin thread link should redirect to form view", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.fake"].create({ name: "Some record" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.fake",
        needaction: true,
        res_id: fakeId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    const def = new Deferred();
    mockService("action", {
        async doAction(action) {
            if (action?.res_model !== "res.fake") {
                return super.doAction(...arguments);
            }
            // Callback of doing an action (action manager).
            // Expected to be called on click on origin thread link,
            // which redirects to form view of record related to origin thread
            step("do-action");
            expect(action.type).toBe("ir.actions.act_window");
            expect(action.views).toEqual([[false, "form"]]);
            expect(action.res_model).toBe("res.fake");
            expect(action.res_id).toBe(fakeId);
            def.resolve();
        },
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-Message");
    await click(".o-mail-Message-header a", { text: "Some record" });
    await def;
    await assertSteps(["do-action"]);
});

test("inbox messages are never squashed", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            author_id: partnerId,
            body: "<p>body1</p>",
            date: "2019-04-20 10:00:00",
            message_type: "comment",
            model: "discuss.channel",
            needaction: true,
            res_id: channelId,
        },
        {
            author_id: partnerId,
            body: "<p>body2</p>",
            date: "2019-04-20 10:00:30",
            message_type: "comment",
            model: "discuss.channel",
            needaction: true,
            res_id: channelId,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
        {
            mail_message_id: messageId_2,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    await start();
    await openDiscuss();
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Message:not(.o-squashed)", { text: "body1" });
    await contains(".o-mail-Message:not(.o-squashed)", { text: "body2" });
    await click(".o-mail-DiscussSidebarChannel", { text: "test" });
    await contains(".o-mail-Message.o-squashed", { text: "body2" });
});

test("reply: stop replying button click", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
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
    await openDiscuss();
    await contains(".o-mail-Message");
    await click("[title='Reply']");
    await contains(".o-mail-Composer");
    await contains("i[title='Stop replying']");
    await click("i[title='Stop replying']");
    await contains(".o-mail-Composer", { count: 0 });
});

test("error notifications should not be shown in Inbox", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        needaction: true,
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "email",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-header small", { text: "on Demo User" });
    await contains(`.o-mail-Message-header a[href*='/odoo/res.partner/${partnerId}']`, {
        text: "Demo User",
    });
    await contains(".o-mail-Message-notification", { count: 0 });
});

test("emptying inbox displays rainbow man in inbox", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const messageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        needaction: true,
        res_id: channelId,
    });
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId1,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    await start();
    await openDiscuss();
    await contains(".o-mail-Message");
    await click("button:enabled", { text: "Mark all read" });
    await contains(".o_reward_rainbow");
});

test("emptying inbox doesn't display rainbow man in another thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const partnerId = pyEnv["res.partner"].create({});
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        needaction: true,
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await contains("button", { text: "Inbox", contains: [".badge", { text: "1" }] });
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(partner, "mail.message/mark_as_read", {
        message_ids: [messageId],
        needaction_inbox_counter: 0,
    });
    await contains("button", { text: "Inbox", contains: [".badge", { count: 0 }] });
    // weak test, no guarantee that we waited long enough for the potential rainbow man to show
    await contains(".o_reward_rainbow", { count: 0 });
});

test("Counter should be incremented by 1 when receiving a message with a mention in a channel", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], { notification_type: "inbox" });
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const partnerId = pyEnv["res.partner"].create({ name: "Thread" });
    const partnerUserId = pyEnv["res.partner"].create({ name: "partner1" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerUserId });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        needaction: true,
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    await start();
    await openDiscuss();
    await contains("button", { text: "Inbox", contains: [".badge", { text: "1" }] });
    const mention = [serverState.partnerId];
    const mentionName = serverState.partnerName;
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: `<a href="https://www.hoot.test/odoo/res.partner/17" class="o_mail_redirect" data-oe-id="${mention[0]}" data-oe-model="res.partner" target="_blank" contenteditable="false">@${mentionName}</a> mention`,
                message_type: "comment",
                partner_ids: mention,
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains("button", { text: "Inbox", contains: [".badge", { text: "2" }] });
});

test("Clear need action counter when opening a channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const [messageId1, messageId2] = pyEnv["mail.message"].create([
        {
            body: "not empty",
            model: "discuss.channel",
            needaction: true,
            res_id: channelId,
        },
        {
            body: "not empty",
            model: "discuss.channel",
            needaction: true,
            res_id: channelId,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId1,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
        {
            mail_message_id: messageId2,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebar-item", {
        text: "General",
        contains: [".badge", { text: "2" }],
    });
    await click(".o-mail-DiscussSidebarChannel", { text: "General" });
    await contains(".o-mail-DiscussSidebar-item", {
        text: "General",
        contains: [".badge", { count: 0 }],
    });
});

test("can reply to email message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const messageId = pyEnv["mail.message"].create({
        author_id: null,
        email_from: "md@oilcompany.fr",
        body: "an email message",
        model: "res.partner",
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
    await openDiscuss();
    await contains(".o-mail-Message");
    await click("[title='Reply']");
    await contains(".o-mail-Composer", { text: "Replying to md@oilcompany.fr" });
});
