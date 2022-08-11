/** @odoo-module **/

import {
    afterNextRender,
    nextAnimationFrame,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import { patchWithCleanup } from '@web/../tests/helpers/utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_inbox_tests.js');

QUnit.test('reply: discard on pressing escape', async function (assert) {
    assert.expect(9);

    const pyEnv = await startServer();
    // partner expected to be found by mention
    pyEnv['res.partner'].create({
        email: "testpartnert@odoo.com",
        name: "TestPartner",
    });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: 20,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, click, insertText, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );
    await click('.o_Message');
    await click('.o_MessageActionList_actionReply');
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "should have composer after clicking on reply to message"
    );

    await click(`.o_Composer_buttonEmojis`);
    assert.containsOnce(
        document.body,
        '.o_EmojiPickerView',
        "emoji list should be opened after click on emojis button"
    );

    await afterNextRender(() => {
        const ev = new window.KeyboardEvent('keydown', { bubbles: true, key: "Escape" });
        document.querySelector(`.o_Composer_buttonEmojis`).dispatchEvent(ev);
    });
    assert.containsNone(
        document.body,
        '.o_EmojiPickerView',
        "emoji list should be closed after pressing escape on emojis button"
    );
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "reply composer should still be opened after pressing escape on emojis button"
    );

    await insertText('.o_ComposerTextInput_textarea', "@Te");
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestionView',
        "mention suggestion should be opened after typing @"
    );

    await afterNextRender(() => {
        const ev = new window.KeyboardEvent('keydown', { bubbles: true, key: "Escape" });
        document.querySelector(`.o_ComposerTextInput_textarea`).dispatchEvent(ev);
    });
    assert.containsNone(
        document.body,
        '.o_ComposerSuggestionView',
        "mention suggestion should be closed after pressing escape on mention suggestion"
    );
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "reply composer should still be opened after pressing escape on mention suggestion"
    );

    await afterNextRender(() => {
        const ev = new window.KeyboardEvent('keydown', { bubbles: true, key: "Escape" });
        document.querySelector(`.o_ComposerTextInput_textarea`).dispatchEvent(ev);
    });
    assert.containsNone(
        document.body,
        '.o_Composer',
        "reply composer should be closed after pressing escape if there was no other priority escape handler"
    );
});

QUnit.test('reply: discard on discard button click', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, click, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );
    await click('.o_Message');

    await click('.o_MessageActionList_actionReply');
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "should have composer after clicking on reply to message"
    );
    assert.containsOnce(
        document.body,
        '.o_Composer_buttonDiscard',
        "composer should have a discard button"
    );

    await click(`.o_Composer_buttonDiscard`);
    assert.containsNone(
        document.body,
        '.o_Composer',
        "reply composer should be closed after clicking on discard"
    );
});

QUnit.test('reply: discard on reply button toggle', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, click, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );

    await click('.o_Message');
    await click('.o_MessageActionList_actionReply');
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "should have composer after clicking on reply to message"
    );
    await click(`.o_MessageActionList_actionReply`);
    assert.containsNone(
        document.body,
        '.o_Composer',
        "reply composer should be closed after clicking on reply button again"
    );
});

QUnit.test('reply: discard on click away', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, click, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );

    await click('.o_Message');
    await click('.o_MessageActionList_actionReply');
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "should have composer after clicking on reply to message"
    );

    document.querySelector(`.o_ComposerTextInput_textarea`).click();
    await nextAnimationFrame(); // wait just in case, but nothing is supposed to happen
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "reply composer should still be there after clicking inside itself"
    );

    await click(`.o_Composer_buttonEmojis`);
    assert.containsOnce(
        document.body,
        '.o_EmojiPickerView',
        "emoji list should be opened after clicking on emojis button"
    );

    await click(`.o_Emoji`);
    assert.containsNone(
        document.body,
        '.o_EmojiPickerView',
        "emoji list should be closed after selecting an emoji"
    );
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "reply composer should still be there after selecting an emoji (even though it is technically a click away, it should be considered inside)"
    );

    await click(`.o_Message`);
    assert.containsNone(
        document.body,
        '.o_Composer',
        "reply composer should be closed after clicking away"
    );
});

QUnit.test('"reply to" composer should log note if message replied to is a note', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        is_discussion: false,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, click, insertText, messaging, openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === '/mail/message/post') {
                assert.step('/mail/message/post');
                assert.strictEqual(
                    args.post_data.message_type,
                    "comment",
                    "should set message type as 'comment'"
                );
                assert.strictEqual(
                    args.post_data.subtype_xmlid,
                    "mail.mt_note",
                    "should set subtype_xmlid as 'note'"
                );
            }
        },
    });
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );

    await click('.o_Message');
    await click('.o_MessageActionList_actionReply');
    assert.strictEqual(
        document.querySelector('.o_Composer_buttonSend').textContent.trim(),
        "Log",
        "Send button text should be 'Log'"
    );

    await insertText('.o_ComposerTextInput_textarea', "Test");
    await click('.o_Composer_buttonSend');
    assert.verifySteps(['/mail/message/post']);
});

QUnit.test('"reply to" composer should send message if message replied to is not a note', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        is_discussion: true,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, click, insertText, messaging, openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === '/mail/message/post') {
                assert.step('/mail/message/post');
                assert.strictEqual(
                    args.post_data.message_type,
                    "comment",
                    "should set message type as 'comment'"
                );
                assert.strictEqual(
                    args.post_data.subtype_xmlid,
                    "mail.mt_comment",
                    "should set subtype_xmlid as 'comment'"
                );
            }
        },
    });
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );

    await click('.o_Message');
    await click('.o_MessageActionList_actionReply');
    assert.strictEqual(
        document.querySelector('.o_Composer_buttonSend').textContent.trim(),
        "Send",
        "Send button text should be 'Send'"
    );

    await insertText('.o_ComposerTextInput_textarea', "Test");
    await click('.o_Composer_buttonSend');
    assert.verifySteps(['/mail/message/post']);
});

QUnit.test('error notifications should not be shown in Inbox', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'mail.channel',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1, // id of related message
        notification_status: 'exception',
        notification_type: 'email',
        res_partner_id: pyEnv.currentPartnerId, // must be for current partner
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_originThreadLink',
        "should display origin thread link"
    );
    assert.containsNone(
        document.body,
        '.o_Message_notificationIcon',
        "should not display any notification icon in Inbox"
    );
});

QUnit.test('show subject of message in Inbox', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'mail.channel',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId], // not needed, for consistency
        subject: "Salutations, voyageur",
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_subject',
        "should display subject of the message"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_subject').textContent,
        "Subject: Salutations, voyageur",
        "Subject of the message should be 'Salutations, voyageur'"
    );
});

QUnit.test('show subject of message in history', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        history_partner_ids: [3], // not needed, for consistency
        model: 'mail.channel',
        subject: "Salutations, voyageur",
    });
    pyEnv['mail.notification'].create({
        is_read: true,
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, messaging, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: 'mail.box_history',
            },
        },
    });
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until history displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.history.thread
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_subject',
        "should display subject of the message"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_subject').textContent,
        "Subject: Salutations, voyageur",
        "Subject of the message should be 'Salutations, voyageur'"
    );
});

QUnit.test('click on (non-channel/non-partner) origin thread link should redirect to form view', async function (assert) {
    assert.expect(9);

    const pyEnv = await startServer();
    const resFakeId1 = pyEnv['res.fake'].create({ name: 'Some record' });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'res.fake',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resFakeId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, env, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    patchWithCleanup(env.services.action, {
        doAction(action) {
            // Callback of doing an action (action manager).
            // Expected to be called on click on origin thread link,
            // which redirects to form view of record related to origin thread
            assert.step('do-action');
            assert.strictEqual(
                action.type,
                'ir.actions.act_window',
                "action should open a view"
            );
            assert.deepEqual(
                action.views,
                [[false, 'form']],
                "action should open form view"
            );
            assert.strictEqual(
                action.res_model,
                'res.fake',
                "action should open view with model 'res.fake' (model of message origin thread)"
            );
            assert.strictEqual(
                action.res_id,
                resFakeId1,
                "action should open view with id of resFake1 (id of message origin thread)"
            );
            return Promise.resolve();
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_originThreadLink',
        "should display origin thread link"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_originThreadLink').textContent,
        "Some record",
        "origin thread link should display record name"
    );

    document.querySelector('.o_Message_originThreadLink').click();
    assert.verifySteps(['do-action'], "should have made an action on click on origin thread (to open form view)");
});

QUnit.test('subject should not be shown when subject is the same as the thread name', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: "Salutations, voyageur" });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'mail.channel',
        res_id: mailChannelId1,
        needaction: true,
        subject: "Salutations, voyageur",
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message_subject',
        "subject should not be shown when subject is the same as the thread name"
    );
});

QUnit.test('subject should not be shown when subject is the same as the thread name and both have the same prefix', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: "Re: Salutations, voyageur" });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'mail.channel',
        res_id: mailChannelId1,
        needaction: true,
        subject: "Re: Salutations, voyageur",
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message_subject',
        "subject should not be shown when subject is the same as the thread name and both have the same prefix"
    );
});

QUnit.test('subject should not be shown when subject differs from thread name only by the "Re:" prefix', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: "Salutations, voyageur" });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'mail.channel',
        res_id: mailChannelId1,
        needaction: true,
        subject: "Re: Salutations, voyageur",
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message_subject',
        "should not display subject when subject differs from thread name only by the 'Re:' prefix"
    );
});

QUnit.test('subject should not be shown when subject differs from thread name only by the "Fw:" and "Re:" prefix', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: "Salutations, voyageur" });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'mail.channel',
        res_id: mailChannelId1,
        needaction: true,
        subject: "Fw: Re: Salutations, voyageur",
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message_subject',
        "should not display subject when subject differs from thread name only by the 'Fw:' and Re:' prefix"
    );
});

QUnit.test('subject should be shown when the thread name has an extra prefix compared to subject', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: "Re: Salutations, voyageur" });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'mail.channel',
        res_id: mailChannelId1,
        needaction: true,
        subject: "Salutations, voyageur",
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message_subject',
        "subject should be shown when the thread name has an extra prefix compared to subject"
    );
});

QUnit.test('subject should not be shown when subject differs from thread name only by the "fw:" prefix and both contain another common prefix', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: "Re: Salutations, voyageur" });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'mail.channel',
        res_id: mailChannelId1,
        needaction: true,
        subject: "fw: re: Salutations, voyageur",
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message_subject',
        "subject should not be shown when subject differs from thread name only by the 'fw:' prefix and both contain another common prefix"
    );
});

QUnit.test('subject should not be shown when subject differs from thread name only by the "Re: Re:" prefix', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: "Salutations, voyageur" });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'mail.channel',
        res_id: mailChannelId1,
        needaction: true,
        subject: "Re: Re: Salutations, voyageur",
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message_subject',
        "should not display subject when subject differs from thread name only by the 'Re: Re:'' prefix"
    );
});

});
});
