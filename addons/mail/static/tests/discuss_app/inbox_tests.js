/* @odoo-module */

import {
    afterNextRender,
    click,
    insertText,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";
import { DEBOUNCE_FETCH_SUGGESTION_TIME } from "@mail/core/common/suggestion_service";

import {
    patchWithCleanup,
    triggerHotkey,
    mockTimeout,
    nextTick,
} from "@web/../tests/helpers/utils";

QUnit.module("discuss inbox");

QUnit.test("reply: discard on reply button toggle", async (assert) => {
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
    await openDiscuss();
    assert.containsOnce($, ".o-mail-Message");

    await click("[title='Reply']");
    assert.containsOnce($, ".o-mail-Composer");
    await click("[title='Reply']");
    assert.containsNone($, ".o-mail-Composer");
});

QUnit.test("reply: discard on pressing escape", async (assert) => {
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
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss();
    assert.containsOnce($, ".o-mail-Message");

    await click(".o-mail-Message [title='Reply']");
    assert.containsOnce($, ".o-mail-Composer");

    // Escape on emoji picker does not stop replying
    await click(".o-mail-Composer button[aria-label='Emojis']");
    assert.containsOnce($, ".o-mail-EmojiPicker");
    await afterNextRender(() => triggerHotkey("Escape"));
    assert.containsNone($, ".o-mail-EmojiPicker");
    assert.containsOnce($, ".o-mail-Composer");

    // Escape on suggestion prompt does not stop replying
    await insertText(".o-mail-Composer-input", "@");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await nextTick();
    assert.containsOnce($, ".o-mail-Composer-suggestionList .o-open");
    await afterNextRender(() => triggerHotkey("Escape"));
    assert.containsNone($, ".o-mail-Composer-suggestionList .o-open");
    assert.containsOnce($, ".o-mail-Composer");

    click(".o-mail-Composer-input").catch(() => {});
    await afterNextRender(() => triggerHotkey("Escape"));
    assert.containsNone($, ".o-mail-Composer");
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
        await openDiscuss();
        assert.containsOnce($, ".o-mail-Message");

        await click("[title='Reply']");
        await insertText(".o-mail-Composer-input", "Test");
        await click(".o-mail-Composer-send");
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
        await openDiscuss();
        assert.containsOnce($, ".o-mail-Message");

        await click("[title='Reply']");
        assert.strictEqual($(".o-mail-Composer-send").text().trim(), "Send");

        await insertText(".o-mail-Composer-input", "Test");
        await click(".o-mail-Composer-send");
        assert.verifySteps(["/mail/message/post"]);
    }
);

QUnit.test("show subject of message in Inbox", async (assert) => {
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
    await openDiscuss();
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message:contains(Subject: Salutations, voyageur)");
});

QUnit.test("show subject of message in history", async (assert) => {
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
    await openDiscuss("mail.box_history");
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message:contains(Subject: Salutations, voyageur)");
});

QUnit.test(
    "subject should not be shown when subject is the same as the thread name",
    async (assert) => {
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
        await openDiscuss("mail.box_inbox");
        assert.containsNone($, ".o-mail-Message-content:contains(Salutations, voyageur)");
    }
);

QUnit.test(
    "subject should not be shown when subject is the same as the thread name and both have the same prefix",
    async (assert) => {
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
        await openDiscuss("mail.box_inbox");
        assert.containsNone($, ".o-mail-Message-content:contains(Salutations, voyageur)");
    }
);

QUnit.test(
    'subject should not be shown when subject differs from thread name only by the "Re:" prefix',
    async (assert) => {
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
        await openDiscuss("mail.box_inbox");
        assert.containsNone($, ".o-mail-Message-content:contains(Salutations, voyageur)");
    }
);

QUnit.test(
    'subject should not be shown when subject differs from thread name only by the "Fw:" and "Re:" prefix',
    async (assert) => {
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
        await openDiscuss("mail.box_inbox");
        assert.containsNone($, ".o-mail-Message-contente:contains(Salutations, voyageur)");
    }
);

QUnit.test(
    "subject should be shown when the thread name has an extra prefix compared to subject",
    async (assert) => {
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
        await openDiscuss("mail.box_inbox");
        assert.containsNone($, ".o-mail-Message-content:contains(Salutations, voyageur)");
    }
);

QUnit.test(
    'subject should not be shown when subject differs from thread name only by the "fw:" prefix and both contain another common prefix',
    async (assert) => {
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
        await openDiscuss("mail.box_inbox");
        assert.containsNone($, ".o-mail-Message-content:contains(Salutations, voyageur)");
    }
);

QUnit.test(
    'subject should not be shown when subject differs from thread name only by the "Re: Re:" prefix',
    async (assert) => {
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
        await openDiscuss("mail.box_inbox");
        assert.containsNone($, ".o-mail-Message-content:contains(Salutations, voyageur)");
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
    await openDiscuss();
    assert.containsOnce($, "button:contains(Inbox) .badge:contains(2)");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(General) .badge:contains(2)");
    assert.containsN($, ".o-mail-Discuss-content .o-mail-Message", 2);
    assert.notOk($("button:contains(Mark all read)")[0].disabled);

    await click(".o-mail-Discuss-header button:contains(Mark all read)");
    assert.containsNone($, "button:contains(Inbox) .badge");
    assert.containsNone($, ".o-mail-DiscussCategoryItem:contains(General) .badge");
    assert.containsNone($, ".o-mail-Message");
    assert.ok($("button:contains(Mark all read)")[0].disabled);
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
        await openDiscuss();
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
                return Promise.resolve();
            },
        });
        assert.containsOnce($, ".o-mail-Message");
        assert.containsOnce($, ".o-mail-Message-header a:contains(Some record)");

        click(".o-mail-Message-header a:contains(Some record)").catch(() => {});
        assert.verifySteps(["do-action"]);
    }
);

QUnit.test("inbox messages are never squashed", async (assert) => {
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
    await openDiscuss();
    assert.containsN($, ".o-mail-Message", 2);
    assert.doesNotHaveClass($(".o-mail-Message:contains(body1)"), "o-squashed");
    assert.doesNotHaveClass($(".o-mail-Message:contains(body2)"), "o-squashed");
    await click(".o-mail-DiscussCategoryItem:contains(test)");
    assert.hasClass($(".o-mail-Message:contains(body2)"), "o-squashed");
});

QUnit.test("reply: stop replying button click", async (assert) => {
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
    await openDiscuss();
    assert.containsOnce($, ".o-mail-Message");

    await click("[title='Reply']");
    assert.containsOnce($, ".o-mail-Composer");
    assert.containsOnce($, "i[title='Stop replying']");

    await click("i[title='Stop replying']");
    assert.containsNone($, ".o-mail-Composer");
});

QUnit.test("error notifications should not be shown in Inbox", async (assert) => {
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
    await openDiscuss();
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message-header:contains(on Demo User)");
    assert.containsOnce(
        $,
        `.o-mail-Message-header a:contains(Demo User)[href*='/web#model=res.partner&id=${partnerId}']`
    );
    assert.containsNone($, ".o-mail-Message-notification");
});

QUnit.test("emptying inbox displays rainbow man in inbox", async (assert) => {
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
    await openDiscuss();
    await click("button:contains(Mark all read)");
    assert.containsOnce($, ".o_reward_rainbow");
});

QUnit.test("emptying inbox doesn't display rainbow man in another thread", async (assert) => {
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
    await openDiscuss(channelId);
    assert.containsOnce($, "button:contains(Inbox) .badge:contains(1)");
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.message/mark_as_read", {
        message_ids: [messageId],
        needaction_inbox_counter: 0,
    });
    await afterNextRender(() => mockTimeout().execRegisteredTimeouts);
    assert.containsNone($, "button:contains(Inbox) .badge");
    assert.containsNone($, ".o_reward_rainbow");
});
