/** @odoo-module **/

import {
    afterNextRender,
    click,
    insertText,
    nextAnimationFrame,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";

import { getFixture, patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";

let target;

QUnit.module("discuss inbox", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("reply: discard on reply button toggle", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({});
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resPartnerId1,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: mailMessageId1,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, ".o-mail-message");

    await click("i[aria-label='Reply']");
    assert.containsOnce(target, ".o-mail-composer");
    await click("i[aria-label='Reply']");
    assert.containsNone(target, ".o-mail-composer");
});

QUnit.test("reply: discard on click away", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({});
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resPartnerId1,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: mailMessageId1,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, ".o-mail-message");

    await click("i[aria-label='Reply']");
    assert.containsOnce(target, ".o-mail-composer");

    document.querySelector(".o-mail-composer-textarea").click();
    await nextAnimationFrame(); // wait just in case, but nothing is supposed to happen
    assert.containsOnce(
        target,
        ".o-mail-composer",
        "reply composer should still be there after clicking inside itself"
    );

    await click("i[aria-label='Emojis']");
    assert.containsOnce(target, ".o-mail-emoji-picker");

    await click(".o-mail-emoji-picker-content .o-emoji");
    assert.containsNone(target, ".o-mail-emoji-picker");
    assert.containsOnce(
        target,
        ".o-mail-composer",
        "reply composer should still be there after selecting an emoji (even though it is technically a click away, it should be considered inside)"
    );

    await click(".o-mail-message");
    assert.containsNone(target, ".o-mail-composer");
});

QUnit.test("reply: discard on pressing escape", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["res.partner"].create({
        email: "testpartnert@odoo.com",
        name: "TestPartner",
    });
    const mailMessageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: 20,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: mailMessageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, ".o-mail-message");

    await click(".o-mail-message-actions i[aria-label='Reply']");
    assert.containsOnce(target, ".o-mail-composer");

    // Escape on emoji picker does not stop replying
    await click(".o-mail-composer i[aria-label='Emojis']");
    assert.containsOnce(target, ".o-mail-emoji-picker");
    await afterNextRender(() => triggerHotkey("Escape"));
    assert.containsNone(target, ".o-mail-emoji-picker");
    assert.containsOnce(target, ".o-mail-composer");

    // Escape on suggestion prompt does not stop replying
    await insertText(".o-mail-composer-textarea", "@");
    assert.containsOnce(target, ".o-composer-suggestion-list .o-open");
    await afterNextRender(() => triggerHotkey("Escape"));
    assert.containsNone(target, ".o-composer-suggestion-list .o-open");
    assert.containsOnce(target, ".o-mail-composer");

    click(".o-mail-composer-textarea").catch(() => {});
    await afterNextRender(() => triggerHotkey("Escape"));
    assert.containsNone(target, ".o-mail-composer");
});

QUnit.test(
    '"reply to" composer should log note if message replied to is a note',
    async function (assert) {
        const pyEnv = await startServer();
        const resPartnerId1 = pyEnv["res.partner"].create({});
        const mailMessageId1 = pyEnv["mail.message"].create({
            body: "not empty",
            is_note: true,
            model: "res.partner",
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: resPartnerId1,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: mailMessageId1,
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
        assert.containsOnce(target, ".o-mail-message");

        await click("i[aria-label='Reply']");
        await insertText(".o-mail-composer-textarea", "Test");
        await click(".o-mail-composer-send-button");
        assert.verifySteps(["/mail/message/post"]);
    }
);

QUnit.test(
    '"reply to" composer should send message if message replied to is not a note',
    async function (assert) {
        const pyEnv = await startServer();
        const resPartnerId1 = pyEnv["res.partner"].create({});
        const mailMessageId1 = pyEnv["mail.message"].create({
            body: "not empty",
            is_discussion: true,
            model: "res.partner",
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: resPartnerId1,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: mailMessageId1,
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
        assert.containsOnce(target, ".o-mail-message");

        await click("i[aria-label='Reply']");
        assert.strictEqual(
            document.querySelector(".o-mail-composer-send-button").textContent.trim(),
            "Send"
        );

        await insertText(".o-mail-composer-textarea", "Test");
        await click(".o-mail-composer-send-button");
        assert.verifySteps(["/mail/message/post"]);
    }
);

QUnit.test("show subject of message in Inbox", async function (assert) {
    const pyEnv = await startServer();
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        model: "mail.channel",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId], // not needed, for consistency
        subject: "Salutations, voyageur",
    });
    pyEnv["mail.notification"].create({
        mail_message_id: mailMessageId1,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, ".o-mail-message");
    assert.containsOnce(target, ".o-mail-message-subject");
    assert.strictEqual(
        target.querySelector(".o-mail-message-subject").textContent,
        "Subject: Salutations, voyageur"
    );
});

QUnit.test("show subject of message in history", async function (assert) {
    const pyEnv = await startServer();
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        history_partner_ids: [3], // not needed, for consistency
        model: "mail.channel",
        subject: "Salutations, voyageur",
    });
    pyEnv["mail.notification"].create({
        is_read: true,
        mail_message_id: mailMessageId1,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss("mail.box_history");
    assert.containsOnce(target, ".o-mail-message");
    assert.containsOnce(target, ".o-mail-message-subject");
    assert.strictEqual(
        target.querySelector(".o-mail-message-subject").textContent,
        "Subject: Salutations, voyageur"
    );
});

QUnit.test(
    "subject should not be shown when subject is the same as the thread name",
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({
            name: "Salutations, voyageur",
        });
        const mailMessageId1 = pyEnv["mail.message"].create({
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId1,
            needaction: true,
            subject: "Salutations, voyageur",
        });
        pyEnv["mail.notification"].create({
            mail_message_id: mailMessageId1,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start();
        await openDiscuss("mail.box_inbox");
        assert.containsNone(target, ".o-mail-message-subject");
    }
);

QUnit.test(
    "subject should not be shown when subject is the same as the thread name and both have the same prefix",
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({
            name: "Re: Salutations, voyageur",
        });
        const mailMessageId1 = pyEnv["mail.message"].create({
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId1,
            needaction: true,
            subject: "Re: Salutations, voyageur",
        });
        pyEnv["mail.notification"].create({
            mail_message_id: mailMessageId1,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start();
        await openDiscuss("mail.box_inbox");
        assert.containsNone(target, ".o-mail-message-subject");
    }
);

QUnit.test(
    'subject should not be shown when subject differs from thread name only by the "Re:" prefix',
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({
            name: "Salutations, voyageur",
        });
        const mailMessageId1 = pyEnv["mail.message"].create({
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId1,
            needaction: true,
            subject: "Re: Salutations, voyageur",
        });
        pyEnv["mail.notification"].create({
            mail_message_id: mailMessageId1,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start();
        await openDiscuss("mail.box_inbox");
        assert.containsNone(target, ".o-mail-message-subject");
    }
);

QUnit.test(
    'subject should not be shown when subject differs from thread name only by the "Fw:" and "Re:" prefix',
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({
            name: "Salutations, voyageur",
        });
        const mailMessageId1 = pyEnv["mail.message"].create({
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId1,
            needaction: true,
            subject: "Fw: Re: Salutations, voyageur",
        });
        pyEnv["mail.notification"].create({
            mail_message_id: mailMessageId1,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start();
        await openDiscuss("mail.box_inbox");
        assert.containsNone(target, ".o-mail-message-subject");
    }
);

QUnit.test(
    "subject should be shown when the thread name has an extra prefix compared to subject",
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({
            name: "Re: Salutations, voyageur",
        });
        const mailMessageId1 = pyEnv["mail.message"].create({
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId1,
            needaction: true,
            subject: "Salutations, voyageur",
        });
        pyEnv["mail.notification"].create({
            mail_message_id: mailMessageId1,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start();
        await openDiscuss("mail.box_inbox");
        assert.containsOnce(target, ".o-mail-message-subject");
    }
);

QUnit.test(
    'subject should not be shown when subject differs from thread name only by the "fw:" prefix and both contain another common prefix',
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({
            name: "Re: Salutations, voyageur",
        });
        const mailMessageId1 = pyEnv["mail.message"].create({
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId1,
            needaction: true,
            subject: "fw: re: Salutations, voyageur",
        });
        pyEnv["mail.notification"].create({
            mail_message_id: mailMessageId1,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start();
        await openDiscuss("mail.box_inbox");
        assert.containsNone(target, ".o-mail-message-subject");
    }
);

QUnit.test(
    'subject should not be shown when subject differs from thread name only by the "Re: Re:" prefix',
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({
            name: "Salutations, voyageur",
        });
        const mailMessageId1 = pyEnv["mail.message"].create({
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId1,
            needaction: true,
            subject: "Re: Re: Salutations, voyageur",
        });
        pyEnv["mail.notification"].create({
            mail_message_id: mailMessageId1,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start();
        await openDiscuss("mail.box_inbox");
        assert.containsNone(target, ".o-mail-message-subject");
    }
);

QUnit.test("inbox: mark all messages as read", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({});
    const [mailMessageId1, mailMessageId2] = pyEnv["mail.message"].create([
        {
            body: "not empty",
            model: "mail.channel",
            needaction: true,
            res_id: mailChannelId1,
        },
        {
            body: "not empty",
            model: "mail.channel",
            needaction: true,
            res_id: mailChannelId1,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: mailMessageId1,
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        },
        {
            mail_message_id: mailMessageId2,
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, 'button[data-mailbox="inbox"] .badge:contains(2)');
    assert.containsOnce(
        target,
        `.o-mail-category-item[data-channel-id="${mailChannelId1}"] .badge:contains(2)`
    );
    assert.containsN(target, ".o-mail-discuss-content .o-mail-message", 2);
    assert.notOk(
        $(target).find('.o-mail-discuss-actions button[data-action="mark-all-read"]')[0].disabled
    );

    await click('.o-mail-discuss-actions button[data-action="mark-all-read"]');
    assert.containsNone(target, 'button[data-mailbox="inbox"] .badge');
    assert.containsNone(
        target,
        `.o-mail-category-item[data-channel-id="${mailChannelId1}"] .badge`
    );
    assert.containsNone(target, ".o-mail-discuss-content .o-mail-message");
    assert.ok(
        $(target).find('.o-mail-discuss-actions button[data-action="mark-all-read"]')[0].disabled
    );
});

QUnit.test(
    "click on (non-channel/non-partner) origin thread link should redirect to form view",
    async function (assert) {
        const pyEnv = await startServer();
        const resFakeId = pyEnv["res.fake"].create({ name: "Some record" });
        const mailMessageId = pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.fake",
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: resFakeId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: mailMessageId,
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
                assert.strictEqual(action.res_id, resFakeId);
                return Promise.resolve();
            },
        });
        assert.containsOnce(document.body, ".o-mail-message");
        assert.containsOnce(document.body, ".o-mail-msg-header a:contains(Some record)");

        click(".o-mail-msg-header a:contains(Some record)").catch(() => {});
        assert.verifySteps(["do-action"]);
    }
);

QUnit.test("inbox messages are never squashed", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({});
    const mailChannelId1 = pyEnv["mail.channel"].create({ name: "test" });
    const [mailMessageId1, mailMessageId2] = pyEnv["mail.message"].create([
        {
            author_id: resPartnerId1,
            body: "<p>body1</p>",
            date: "2019-04-20 10:00:00",
            message_type: "comment",
            model: "mail.channel",
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: mailChannelId1,
        },
        {
            author_id: resPartnerId1,
            body: "<p>body2</p>",
            date: "2019-04-20 10:00:30",
            message_type: "comment",
            model: "mail.channel",
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: mailChannelId1,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: mailMessageId1,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        },
        {
            mail_message_id: mailMessageId2,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsN(target, ".o-mail-discuss-content .o-mail-thread .o-mail-message", 2);
    const message1 = target.querySelector(
        `.o-mail-discuss-content .o-mail-thread .o-mail-message[data-message-id="${mailMessageId1}"]`
    );
    const message2 = target.querySelector(
        `.o-mail-discuss-content .o-mail-thread .o-mail-message[data-message-id="${mailMessageId2}"]`
    );
    assert.doesNotHaveClass(message1, "o-mail-message-is-squashed");
    assert.doesNotHaveClass(message2, "o-mail-message-is-squashed");
    await click(`.o-mail-category-item[data-channel-id="${mailChannelId1}"]`);
    assert.hasClass(
        target.querySelector(
            `.o-mail-discuss-content .o-mail-thread .o-mail-message[data-message-id="${mailMessageId2}"]`
        ),
        "o-mail-message-is-squashed"
    );
});
