/** @odoo-module **/

import { makeDeferred } from '@mail/utils/deferred';
import {
    afterNextRender,
    nextAnimationFrame,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import { patchWithCleanup } from '@web/../tests/helpers/utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('message_tests.js');

QUnit.test('basic rendering', async function (assert) {
    assert.expect(12);

    const pyEnv = await startServer();
    const [threadId, otherPartnerId] = pyEnv['res.partner'].create([{}, { name: 'Demo User' }]);
    const mailMessageId = pyEnv['mail.message'].create({
        author_id: otherPartnerId,
        body: '<p>Test</p>',
        model: 'res.partner',
        res_id: threadId,
    });
    const { openView } = await start();
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.strictEqual(
        document.querySelectorAll('.o_Message').length,
        1,
        "should display a message component"
    );
    const messageEl = document.querySelector('.o_Message');
    assert.strictEqual(
        messageEl.dataset.id,
        mailMessageId.toString(),
        "message component should be linked to message store model"
    );
    assert.strictEqual(
        messageEl.querySelectorAll(`:scope .o_Message_sidebar`).length,
        1,
        "message should have a sidebar"
    );
    assert.strictEqual(
        messageEl.querySelectorAll(`:scope .o_Message_sidebar .o_Message_authorAvatar`).length,
        1,
        "message should have author avatar in the sidebar"
    );
    assert.strictEqual(
        messageEl.querySelector(`:scope .o_Message_authorAvatar`).tagName,
        'IMG',
        "message author avatar should be an image"
    );
    assert.strictEqual(
        messageEl.querySelector(`:scope .o_Message_authorAvatar`).dataset.src,
        `/web/image/res.partner/${otherPartnerId}/avatar_128`,
        "message author avatar should GET image of the related partner"
    );
    assert.strictEqual(
        messageEl.querySelectorAll(`:scope .o_Message_authorName`).length,
        1,
        "message should display author name"
    );
    assert.strictEqual(
        messageEl.querySelector(`:scope .o_Message_authorName`).textContent,
        "Demo User",
        "message should display correct author name"
    );
    assert.strictEqual(
        messageEl.querySelectorAll(`:scope .o_Message_date`).length,
        1,
        "message should display date"
    );
    await afterNextRender(() => messageEl.click());
    assert.strictEqual(
        messageEl.querySelectorAll(`:scope .o_MessageActionList`).length,
        1,
        "message should display list of actions"
    );
    assert.strictEqual(
        messageEl.querySelectorAll(`:scope .o_Message_content`).length,
        1,
        "message should display the content"
    );
    assert.strictEqual(
        messageEl.querySelector(`:scope .o_Message_prettyBody`).innerHTML,
        "<p>Test</p>",
        "message should display the correct content"
    );
});

QUnit.test('Notification Sent', async function (assert) {
    assert.expect(9);

    const pyEnv = await startServer();
    const [threadId, resPartnerId] = pyEnv['res.partner'].create([{}, { name: 'Someone', partner_share: true }]);
    const mailMessageId = pyEnv['mail.message'].create({
        body: 'not empty',
        message_type: 'email',
        model: 'res.partner',
        res_id: threadId,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId,
        notification_status: 'sent',
        notification_type: 'email',
        res_partner_id: resPartnerId,
    });
    const { click, openView } = await start();
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconClickable',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-envelope-o',
        "icon should represent email success"
    );

    await click('.o_Message_notificationIconClickable');
    assert.containsOnce(
        document.body,
        '.o_MessageNotificationPopoverContent',
        "notification popover should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageNotificationPopoverContent_notificationIcon',
        "popover should have one icon"
    );
    assert.hasClass(
        document.querySelector('.o_MessageNotificationPopoverContent_notificationIcon'),
        'fa-check',
        "popover should have the sent icon"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageNotificationPopoverContent_notificationPartnerName',
        "popover should have the partner name"
    );
    assert.strictEqual(
        document.querySelector('.o_MessageNotificationPopoverContent_notificationPartnerName').textContent.trim(),
        "Someone",
        "partner name should be correct"
    );
});

QUnit.test('Notification Error', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const [threadId, resPartnerId] = pyEnv['res.partner'].create([{}, { name: "Someone", partner_share: true }]);
    const mailMessageId = pyEnv['mail.message'].create({
        body: 'not empty',
        message_type: 'email',
        model: 'res.partner',
        res_id: threadId,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId,
        notification_status: 'exception',
        notification_type: 'email',
        res_partner_id: resPartnerId,
    });
    const openResendActionDef = makeDeferred();
    const { env, openView } = await start();
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step('do_action');
            assert.strictEqual(
                action,
                'mail.mail_resend_message_action',
                "action should be the one to resend email"
            );
            assert.strictEqual(
                options.additionalContext.mail_message_to_resend,
                mailMessageId,
                "action should have correct message id"
            );
            openResendActionDef.resolve();
        },
    });

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconClickable',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-envelope',
        "icon should represent email error"
    );
    document.querySelector('.o_Message_notificationIconClickable').click();
    await openResendActionDef;
    assert.verifySteps(
        ['do_action'],
        "should do an action to display the resend email dialog"
    );
});

QUnit.test("'channel_fetch' notification received is correctly handled", async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId = pyEnv['res.partner'].create({});
    const mailChannelId = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId }],
        ],
        channel_type: 'chat',
    });
    pyEnv['mail.message'].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsNone(
        document.body,
        '.o_MessageSeenIndicator_icon',
        "message component should not have any check (V) as message is not yet received"
    );

    const mailChannel1 = pyEnv['mail.channel'].searchRead([['id', '=', mailChannelId]])[0];
    // Simulate received channel fetched notification
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(mailChannel1, 'mail.channel.member/fetched', {
            'channel_id': mailChannelId,
            'last_message_id': 100,
            'partner_id': resPartnerId,
        });
    });

    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator_icon',
        "message seen indicator component should only contain one check (V) as message is just received"
    );
});

QUnit.test("'channel_seen' notification received is correctly handled", async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId = pyEnv['res.partner'].create({});
    const mailChannelId = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId }],
        ],
        channel_type: 'chat',
    });
    pyEnv['mail.message'].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsNone(
        document.body,
        '.o_MessageSeenIndicator_icon',
        "message component should not have any check (V) as message is not yet received"
    );

    const mailChannel1 = pyEnv['mail.channel'].searchRead([['id', '=', mailChannelId]])[0];
    // Simulate received channel seen notification
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(mailChannel1, 'mail.channel.member/seen', {
            'channel_id': mailChannelId,
            'last_message_id': 100,
            'partner_id': resPartnerId,
        });
    });
    assert.containsN(
        document.body,
        '.o_MessageSeenIndicator_icon',
        2,
        "message seen indicator component should contain two checks (V) as message is seen"
    );
});

QUnit.test("'channel_fetch' notification then 'channel_seen' received are correctly handled", async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId = pyEnv['res.partner'].create({ display_name: "Recipient" });
    const mailChannelId = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId }],
        ],
        channel_type: 'chat',
    });
    pyEnv['mail.message'].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsNone(
        document.body,
        '.o_MessageSeenIndicator_icon',
        "message component should not have any check (V) as message is not yet received"
    );

    const mailChannel1 = pyEnv['mail.channel'].searchRead([['id', '=', mailChannelId]])[0];
    // Simulate received channel fetched notification
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(mailChannel1, 'mail.channel.member/fetched', {
            'channel_id': mailChannelId,
            'last_message_id': 100,
            'partner_id': resPartnerId,
        });
    });
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator_icon',
        "message seen indicator component should only contain one check (V) as message is just received"
    );

    // Simulate received channel seen notification
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(mailChannel1, 'mail.channel.member/seen', {
            'channel_id': mailChannelId,
            'last_message_id': 100,
            'partner_id': resPartnerId,
        });
    });
    assert.containsN(
        document.body,
        '.o_MessageSeenIndicator_icon',
        2,
        "message seen indicator component should contain two checks (V) as message is now seen"
    );
});

QUnit.test('do not show message seen indicator on the last message seen by everyone when the current user is not author of the message', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const otherPartnerId = pyEnv['res.partner'].create({ name: 'Demo User' });
    const mailChannelId = pyEnv['mail.channel'].create({
        channel_type: 'chat',
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: otherPartnerId }],
        ],
    });
    const mailMessageId = pyEnv['mail.message'].create({
        author_id: otherPartnerId,
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const memberIds = pyEnv['mail.channel.member'].search([['channel_id', '=', mailChannelId]]);
    pyEnv['mail.channel.member'].write(memberIds, { seen_message_id: mailMessageId });
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsNone(
        document.body,
        '.o_Message_seenIndicator',
        "message component should not have any message seen indicator because the current user is not author"
    );
});

QUnit.test('do not show message seen indicator on all the messages of the current user that are older than the last message seen by everyone', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const otherPartnerId = pyEnv['res.partner'].create({ name: 'Demo User' });
    const mailChannelId = pyEnv['mail.channel'].create({
        channel_type: 'chat',
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: otherPartnerId }],
        ],
    });
    const [beforeLastMailMessageId, lastMailMessageId] = pyEnv['mail.message'].create([
        {
            author_id: pyEnv.currentPartnerId,
            body: "<p>Message before last seen</p>",
            model: 'mail.channel',
            res_id: mailChannelId,
        },
        {
            author_id: pyEnv.currentPartnerId,
            body: "<p>Last seen by everyone</p>",
            model: 'mail.channel',
            res_id: mailChannelId,
        },
    ]);
    const memberIds = pyEnv['mail.channel.member'].search([['channel_id', '=', mailChannelId]]);
    pyEnv['mail.channel.member'].write(memberIds, { seen_message_id: lastMailMessageId });
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();

    assert.containsOnce(
        document.body,
        `.o_Message[data-id=${beforeLastMailMessageId}]`,
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        `.o_Message[data-id=${beforeLastMailMessageId}] .o_Message_seenIndicator`,
        "message component should have a message seen indicator because the current user is author"
    );
    assert.containsNone(
        document.body,
        `.o_Message[data-id=${beforeLastMailMessageId}] .o_MessageSeenIndicator_icon`,
        "message component should not have any check (V) because it is older than the last message seen by everyone"
    );
});

QUnit.test('only show messaging seen indicator if authored by me, after last seen by all message', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const otherPartnerId = pyEnv['res.partner'].create({ name: 'Demo User' });
    const mailChannelId = pyEnv['mail.channel'].create({
        channel_type: 'chat',
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: otherPartnerId }],
        ],
    });
    const mailMessageId = pyEnv['mail.message'].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        res_id: mailChannelId,
        model: 'mail.channel',
    });
    const memberIds = pyEnv['mail.channel.member'].search([['channel_id', '=', mailChannelId]]);
    pyEnv['mail.channel.member'].write(memberIds, {
        fetched_message_id: mailMessageId,
        seen_message_id: mailMessageId - 1,
    });
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_seenIndicator',
        "message component should have a message seen indicator"
    );
    assert.containsN(
        document.body,
        '.o_MessageSeenIndicator_icon',
        1,
        "message component should have one check (V) because the message was fetched by everyone but no other member than author has seen the message"
    );
});

QUnit.test('allow attachment delete on authored message', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const mailChannelId = pyEnv['mail.channel'].create({});
    pyEnv['mail.message'].create({
        attachment_ids: [[0, 0, {
            mimetype: 'image/jpeg',
            name: "BLAH",
            res_id: mailChannelId,
            res_model: 'mail.channel',
        }]],
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const { click, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();

    assert.containsOnce(
        document.body,
        '.o_AttachmentImage',
        "should have an attachment",
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentImage_actionUnlink',
        "should have delete attachment button"
    );

    await click('.o_AttachmentImage_actionUnlink');
    assert.containsOnce(
        document.body,
        '.o_AttachmentDeleteConfirm',
        "An attachment delete confirmation dialog should have been opened"
    );
    assert.strictEqual(
        document.querySelector('.o_AttachmentDeleteConfirm_mainText').textContent,
        `Do you really want to delete "BLAH"?`,
        "Confirmation dialog should contain the attachment delete confirmation text"
    );

    await click('.o_AttachmentDeleteConfirm_confirmButton');
    assert.containsNone(
        document.body,
        '.o_AttachmentCard',
        "should no longer have an attachment",
    );
});

QUnit.test('prevent attachment delete on non-authored message in channels', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const partnerId = pyEnv['res.partner'].create({});
    const mailChannelId = pyEnv['mail.channel'].create({});
    pyEnv['mail.message'].create({
        attachment_ids: [[0, 0, {
            mimetype: 'image/jpeg',
            name: "BLAH",
            res_id: mailChannelId,
            res_model: 'mail.channel',
        }]],
        author_id: partnerId,
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();

    assert.containsOnce(
        document.body,
        '.o_AttachmentImage',
        "should have an attachment",
    );
    assert.containsNone(
        document.body,
        '.o_AttachmentImage_actionUnlink',
        "delete attachment button should not be printed"
    );
});

QUnit.test('allow attachment image download on message', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const irAttachmentId1 = pyEnv['ir.attachment'].create({
        name: "Blah.jpg",
        mimetype: 'image/jpeg',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [irAttachmentId1],
        body: '<p>Test</p>',
        model: 'mail.channel',
        res_id: mailChannelId1,
    });
    const { openDiscuss } = await start({
        discuss: {
            context: {
                active_id: mailChannelId1,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_AttachmentImage_actionDownload',
        "should have download attachment button"
    );
});

QUnit.test('subtype description should be displayed if it is different than body', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const threadId = pyEnv['res.partner'].create({});
    const subtypeId = pyEnv['mail.message.subtype'].create({ description: "Bonjour" });
    pyEnv['mail.message'].create({
        body: "<p>Hello</p>",
        model: 'res.partner',
        res_id: threadId,
        subtype_id: subtypeId,
    });
    const { openView } = await start();
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_Message_content',
        "message should have content"
    );
    assert.strictEqual(
        document.querySelector(`.o_Message_content`).textContent,
        "HelloBonjour",
        "message content should display both body and subtype description when they are different"
    );
});

QUnit.test('subtype description should not be displayed if it is similar to body', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const threadId = pyEnv['res.partner'].create({});
    const subtypeId = pyEnv['mail.message.subtype'].create({ description: "hello" });
    pyEnv['mail.message'].create({
        body: "<p>Hello</p>",
        model: 'res.partner',
        res_id: threadId,
        subtype_id: subtypeId,
    });
    const { openView } = await start();
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_Message_content',
        "message should have content"
    );
    assert.strictEqual(
        document.querySelector(`.o_Message_content`).textContent,
        "Hello",
        "message content should display only body when subtype description is similar"
    );
});

QUnit.test('data-oe-id & data-oe-model link redirection on click', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const threadId = pyEnv['res.partner'].create({});
    pyEnv['mail.message'].create({
        body: `<p><a href="#" data-oe-id="250" data-oe-model="some.model">some.model_250</a></p>`,
        model: 'res.partner',
        res_id: threadId,
    });
    const { env, openView } = await start();
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.strictEqual(
                action.type,
                'ir.actions.act_window',
                "action should open view"
            );
            assert.strictEqual(
                action.res_model,
                'some.model',
                "action should open view on 'some.model' model"
            );
            assert.strictEqual(
                action.res_id,
                250,
                "action should open view on 250"
            );
            assert.step('do-action:openFormView_some.model_250');
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message_content',
        "message should have content"
    );
    assert.containsOnce(
        document.querySelector('.o_Message_content'),
        'a',
        "message content should have a link"
    );

    document.querySelector(`.o_Message_content a`).click();
    assert.verifySteps(
        ['do-action:openFormView_some.model_250'],
        "should have open form view on related record after click on link"
    );
});

QUnit.test('chat with author should be opened after clicking on their avatar', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const [threadId, resPartnerId] = pyEnv['res.partner'].create([{}, {}]);
    pyEnv['res.users'].create({ partner_id: resPartnerId });
    pyEnv['mail.message'].create({
        author_id: resPartnerId,
        body: 'not empty',
        model: 'res.partner',
        res_id: threadId,
    });
    const { click, openView } = await start();
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_Message_authorAvatar',
        "message should have the author avatar"
    );
    assert.hasClass(
        document.querySelector('.o_Message_authorAvatar'),
        'o_redirect',
        "author avatar should have the redirect style"
    );

    await click('.o_Message_authorAvatar');
    assert.containsOnce(
        document.body,
        '.o_ChatWindow_thread',
        "chat window with thread should be opened after clicking on author avatar"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindow_thread').dataset.correspondentId,
        resPartnerId.toString(),
        "chat with author should be opened after clicking on their avatar"
    );
});

QUnit.test('chat with author should be opened after clicking on their name', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId = pyEnv['res.partner'].create({});
    pyEnv['res.users'].create({ partner_id: resPartnerId });
    pyEnv['mail.message'].create({
        author_id: resPartnerId,
        body: 'not empty',
        model: 'res.partner',
        res_id: resPartnerId,
    });
    const { click, openFormView } = await start();
    await openFormView({
        res_model: 'res.partner',
        res_id: resPartnerId,
    });
    assert.containsOnce(
        document.body,
        '.o_Message_authorName',
        "message should have the author name"
    );
    assert.hasClass(
        document.querySelector('.o_Message_authorName'),
        'o_redirect',
        "author name should have the redirect style"
    );

    await click('.o_Message_authorName');
    assert.containsOnce(
        document.body,
        '.o_ChatWindow_thread',
        "chat window with thread should be opened after clicking on author name"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindow_thread').dataset.correspondentId,
        resPartnerId.toString(),
        "chat with author should be opened after clicking on their name"
    );
});

QUnit.test('chat with author should be opened after clicking on their im status icon', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const [threadId, resPartnerId] = pyEnv['res.partner'].create([{}, { im_status: 'online' }]);
    pyEnv['res.users'].create({
        im_status: 'online',
        partner_id: resPartnerId,
    });
    pyEnv['mail.message'].create({
        author_id: resPartnerId,
        body: 'not empty',
        model: 'res.partner',
        res_id: threadId,
    });
    const { advanceTime, click, openView } = await start({
        hasTimeControl: true,
    });
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    await afterNextRender(() => advanceTime(50 * 1000)); // next fetch of im_status
    assert.containsOnce(
        document.body,
        '.o_Message_personaImStatusIcon',
        "message should have the author im status icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_personaImStatusIcon'),
        'o-has-open-chat',
        "author im status icon should have the open chat style"
    );

    await click('.o_Message_personaImStatusIcon');
    assert.containsOnce(
        document.body,
        '.o_ChatWindow_thread',
        "chat window with thread should be opened after clicking on author im status icon"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindow_thread').dataset.correspondentId,
        resPartnerId.toString(),
        "chat with author should be opened after clicking on their im status icon"
    );
});

QUnit.test('open chat with author on avatar click should be disabled when currently chatting with the author', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId = pyEnv['res.partner'].create({});
    pyEnv['res.users'].create({ partner_id: resPartnerId });
    const mailChannelId = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId }],
        ],
        channel_type: 'chat',
    });
    pyEnv['mail.message'].create({
        author_id: resPartnerId,
        body: 'not empty',
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_Message_authorAvatar',
        "message should have the author avatar"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_Message_authorAvatar'),
        'o_redirect',
        "author avatar should not have the redirect style"
    );

    document.querySelector('.o_Message_authorAvatar').click();
    await nextAnimationFrame();
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should have no thread opened after clicking on author avatar when currently chatting with the author"
    );
});

QUnit.test('Chat with partner should be opened after clicking on their mention', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId = pyEnv['res.partner'].create({ name: 'Test Partner', email: 'testpartner@odoo.com' });
    pyEnv['res.users'].create({ partner_id: resPartnerId });
    const { click, insertText, openFormView } = await start();
    await openFormView({
        res_model: 'res.partner',
        res_id: resPartnerId,
    });

    await click('.o_ChatterTopbar_buttonSendMessage');
    await insertText('.o_ComposerTextInput_textarea', "@Te");
    await click('.o_ComposerSuggestionView');
    await click('.o_Composer_buttonSend');
    await click('.o_mail_redirect');
    assert.containsOnce(
        document.body,
        '.o_ChatWindow_thread',
        "chat window with thread should be opened after clicking on partner mention"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindow_thread').dataset.correspondentId,
        resPartnerId.toString(),
        "chat with partner should be opened after clicking on their mention"
    );
});

QUnit.test('Channel should be opened after clicking on its mention', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId = pyEnv['res.partner'].create({});
    pyEnv['mail.channel'].create({ name: 'my-channel' });
    const { click, insertText, openFormView } = await start();
    await openFormView({
        res_model: 'res.partner',
        res_id: resPartnerId,
    });

    await click('.o_ChatterTopbar_buttonSendMessage');
    await insertText('.o_ComposerTextInput_textarea', "#my-channel");
    await click('.o_ComposerSuggestionView');
    await click('.o_Composer_buttonSend');
    await click('.o_channel_redirect');
    assert.containsOnce(
        document.body,
        '.o_ChatWindow_thread',
        "chat window with thread should be opened after clicking on channel mention"
    );
});

QUnit.test('message should not be considered as "clicked" after clicking on its author avatar', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv['res.partner'].create([{}, {}]);
    pyEnv['mail.message'].create({
        author_id: partnerId,
        body: "<p>Test</p>",
        model: 'res.partner',
        res_id: threadId,
    });
    const { openView } = await start();
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    document.querySelector(`.o_Message_authorAvatar`).click();
    await nextAnimationFrame();
    assert.doesNotHaveClass(
        document.querySelector(`.o_Message`),
        'o-clicked',
        "message should not be considered as 'clicked' after clicking on its author avatar"
    );
});

QUnit.test('message should not be considered as "clicked" after clicking on notification failure icon', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const threadId = pyEnv['res.partner'].create({});
    const mailMessageId = pyEnv['mail.message'].create({
        body: 'not empty',
        model: 'res.partner',
        res_id: threadId,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId,
        notification_status: 'exception',
        notification_type: 'email',
    });
    const { env, openView } = await start();
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    patchWithCleanup(env.services.action, {
        // intercept the action: this action is not relevant in the context of this test.
        doAction() {},
    });
    document.querySelector('.o_Message_notificationIconClickable.o-error').click();
    await nextAnimationFrame();
    assert.doesNotHaveClass(
        document.querySelector(`.o_Message`),
        'o-clicked',
        "message should not be considered as 'clicked' after clicking on notification failure icon"
    );
});

});
});
