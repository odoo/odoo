/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup, triggerHotkey, makeDeferred } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("discuss inbox");

QUnit.test("reply: discard on reply button toggle", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-Message");

    await click("[title='Expand']");
    await click("[title='Reply']");
    await contains(".o-mail-Composer");
    await click("[title='Expand']");
    await click("[title='Reply']");
    await contains(".o-mail-Composer", { count: 0 });
});

QUnit.test("reply: discard on pressing escape", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].create({
        email: "testpartnert@odoo.com",
        name: "TestPartner",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: 20,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Reply']");
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

    click(".o-mail-Composer-input").catch(() => {});
    triggerHotkey("Escape");
    await contains(".o-mail-Composer", { count: 0 });
});

QUnit.test(
    '"reply to" composer should log note if message replied to is a note',
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const messageId = pyEnv["mail.message"].create({
            body: "not empty",
            is_note: true,
            model: "res.partner",
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: partnerId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/mail/message/post") {
                    assert.step("/mail/message/post");
                    assert.strictEqual(args.post_data.message_type, "comment");
                    assert.strictEqual(args.post_data.subtype_xmlid, "mail.mt_note");
                }
            },
        });
        openDiscuss();
        await contains(".o-mail-Message");
        await click("[title='Expand']");
        await click("[title='Reply']");
        await contains(".o-mail-Composer [placeholder='Log an internal note…']");
        await insertText(".o-mail-Composer-input", "Test");
        await click(".o-mail-Composer-send:enabled", { text: "Log" });
        await contains(".o-mail-Composer", { count: 0 });
        assert.verifySteps(["/mail/message/post"]);
    }
);

QUnit.test(
    '"reply to" composer should send message if message replied to is not a note',
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const messageId = pyEnv["mail.message"].create({
            body: "not empty",
            is_discussion: true,
            model: "res.partner",
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: partnerId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/mail/message/post") {
                    assert.step("/mail/message/post");
                    assert.strictEqual(args.post_data.message_type, "comment");
                    assert.strictEqual(args.post_data.subtype_xmlid, "mail.mt_comment");
                }
            },
        });
        openDiscuss();
        await contains(".o-mail-Message");
        await click("[title='Expand']");
        await click("[title='Reply']");
        await contains(".o-mail-Composer [placeholder='Send a message to followers…']");
        await insertText(".o-mail-Composer-input", "Test");
        await click(".o-mail-Composer-send:enabled", { text: "Send" });
        await contains(".o-mail-Composer-send", { count: 0 });
        assert.verifySteps(["/mail/message/post"]);
    }
);

QUnit.test("show subject of message in Inbox", async () => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId], // not needed, for consistency
        subject: "Salutations, voyageur",
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-Message", { text: "Subject: Salutations, voyageurnot empty" });
});

QUnit.test("show subject of message in history", async () => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        history_partner_ids: [3], // not needed, for consistency
        model: "discuss.channel",
        subject: "Salutations, voyageur",
    });
    pyEnv["mail.notification"].create({
        is_read: true,
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    openDiscuss("mail.box_history");
    await contains(".o-mail-Message", { text: "Subject: Salutations, voyageurnot empty" });
});

QUnit.test("subject should not be shown when subject is the same as the thread name", async () => {
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
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    openDiscuss("mail.box_inbox");
    await contains(".o-mail-Message");
    await contains(".o-mail-Message", {
        count: 0,
        text: "Subject: Salutations, voyageurnot empty",
    });
});

QUnit.test(
    "subject should not be shown when subject is the same as the thread name and both have the same prefix",
    async () => {
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
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start();
        openDiscuss("mail.box_inbox");
        await contains(".o-mail-Message");
        await contains(".o-mail-Message", {
            count: 0,
            text: "Subject: Salutations, voyageurnot empty",
        });
    }
);

QUnit.test(
    'subject should not be shown when subject differs from thread name only by the "Re:" prefix',
    async () => {
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
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start();
        openDiscuss("mail.box_inbox");
        await contains(".o-mail-Message");
        await contains(".o-mail-Message", {
            count: 0,
            text: "Subject: Salutations, voyageurnot empty",
        });
    }
);

QUnit.test(
    'subject should not be shown when subject differs from thread name only by the "Fw:" and "Re:" prefix',
    async () => {
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
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start();
        openDiscuss("mail.box_inbox");
        await contains(".o-mail-Message");
        await contains(".o-mail-Message", {
            count: 0,
            text: "Subject: Salutations, voyageurnot empty",
        });
    }
);

QUnit.test(
    "subject should be shown when the thread name has an extra prefix compared to subject",
    async () => {
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
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start();
        openDiscuss("mail.box_inbox");
        await contains(".o-mail-Message");
        await contains(".o-mail-Message", {
            count: 0,
            text: "Subject: Salutations, voyageurnot empty",
        });
    }
);

QUnit.test(
    'subject should not be shown when subject differs from thread name only by the "fw:" prefix and both contain another common prefix',
    async () => {
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
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start();
        openDiscuss("mail.box_inbox");
        await contains(".o-mail-Message");
        await contains(".o-mail-Message", {
            count: 0,
            text: "Subject: Salutations, voyageurnot empty",
        });
    }
);

QUnit.test(
    'subject should not be shown when subject differs from thread name only by the "Re: Re:" prefix',
    async () => {
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
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start();
        openDiscuss("mail.box_inbox");
        await contains(".o-mail-Message");
        await contains(".o-mail-Message", {
            count: 0,
            text: "Subject: Salutations, voyageurnot empty",
        });
    }
);

QUnit.test("inbox: mark all messages as read", async (assert) => {
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
            res_partner_id: pyEnv.currentPartnerId,
        },
        {
            mail_message_id: messageId_2,
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        },
    ]);
    const { openDiscuss } = await start();
    openDiscuss();
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

QUnit.test(
    "click on (non-channel/non-partner) origin thread link should redirect to form view",
    async (assert) => {
        const pyEnv = await startServer();
        const fakeId = pyEnv["res.fake"].create({ name: "Some record" });
        const messageId = pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.fake",
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: fakeId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { env, openDiscuss } = await start();
        openDiscuss();
        const def = makeDeferred();
        patchWithCleanup(env.services.action, {
            doAction(action) {
                // Callback of doing an action (action manager).
                // Expected to be called on click on origin thread link,
                // which redirects to form view of record related to origin thread
                assert.step("do-action");
                assert.strictEqual(action.type, "ir.actions.act_window");
                assert.deepEqual(action.views, [[false, "form"]]);
                assert.strictEqual(action.res_model, "res.fake");
                assert.strictEqual(action.res_id, fakeId);
                def.resolve();
                return Promise.resolve();
            },
        });
        await contains(".o-mail-Message");
        await click(".o-mail-Message-header a", { text: "Some record" });
        await def;
        assert.verifySteps(["do-action"]);
    }
);

QUnit.test("inbox messages are never squashed", async () => {
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
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: channelId,
        },
        {
            author_id: partnerId,
            body: "<p>body2</p>",
            date: "2019-04-20 10:00:30",
            message_type: "comment",
            model: "discuss.channel",
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: channelId,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        },
        {
            mail_message_id: messageId_2,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        },
    ]);
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Message:not(.o-squashed)", { text: "body1" });
    await contains(".o-mail-Message:not(.o-squashed)", { text: "body2" });
    await click(".o-mail-DiscussSidebarChannel", { text: "test" });
    await contains(".o-mail-Message.o-squashed", { text: "body2" });
});

QUnit.test("reply: stop replying button click", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-Message");

    await click("[title='Expand']");
    await click("[title='Reply']");
    await contains(".o-mail-Composer");
    await contains("i[title='Stop replying']");

    await click("i[title='Stop replying']");
    await contains(".o-mail-Composer", { count: 0 });
});

QUnit.test("error notifications should not be shown in Inbox", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "email",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-header small", { text: "on Demo User" });
    await contains(`.o-mail-Message-header a[href*='/web#model=res.partner&id=${partnerId}']`, {
        text: "Demo User",
    });
    await contains(".o-mail-Message-notification", { count: 0 });
});

QUnit.test("emptying inbox displays rainbow man in inbox", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const messageId1 = pyEnv["mail.message"].create([
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
            res_partner_id: pyEnv.currentPartnerId,
        },
    ]);
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-Message");
    await click("button:enabled", { text: "Mark all read" });
    await contains(".o_reward_rainbow");
});

QUnit.test("emptying inbox doesn't display rainbow man in another thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const partnerId = pyEnv["res.partner"].create({});
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId,
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        },
    ]);
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains("button", { text: "Inbox", contains: [".badge", { text: "1" }] });
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.message/mark_as_read", {
        message_ids: [messageId],
        needaction_inbox_counter: 0,
    });
    await contains("button", { text: "Inbox", contains: [".badge", { count: 0 }] });
    // weak test, no guarantee that we waited long enough for the potential rainbow man to show
    await contains(".o_reward_rainbow", { count: 0 });
});

QUnit.test("Counter should be incremented by 1 when receiving a message with a mention in a channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const partnerId = pyEnv["res.partner"].create({ name: "Thread" });
    const partnerUserId = pyEnv["res.partner"].create({ name: "partner1" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerUserId });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId,
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        },
    ]);
    const { openDiscuss, env } = await start();
    await openDiscuss();
    await contains("button", { text: "Inbox", contains: [".badge", { text: "1" }] });
    const mention = [pyEnv.currentPartnerId];
    const mentionName = pyEnv.currentPartner.name;
    pyEnv.withUser(userId, () =>
        env.services.rpc("/mail/message/post", {
            post_data: {
                body: `<a href="https://www.hoot.test/web#model=res.partner&amp;id=17" class="o_mail_redirect" data-oe-id="${mention[0]}" data-oe-model="res.partner" target="_blank" contenteditable="false">@${mentionName}</a> mention`,
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
