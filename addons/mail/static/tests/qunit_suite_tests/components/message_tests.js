/** @odoo-module **/

import { insert, insertAndReplace, link, replace } from '@mail/model/model_field_command';
import { makeDeferred } from '@mail/utils/deferred';
import {
    afterNextRender,
    createRootMessagingComponent,
    nextAnimationFrame,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import Bus from 'web.Bus';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('message_tests.js');

QUnit.test('basic rendering', async function (assert) {
    assert.expect(12);

    const { createMessageComponent, messaging } = await start();
    const message = messaging.models['Message'].create({
        author: insert({ id: 7, display_name: "Demo User" }),
        body: "<p>Test</p>",
        date: moment(),
        id: 100,
    });
    await createMessageComponent(message);
    assert.strictEqual(
        document.querySelectorAll('.o_Message').length,
        1,
        "should display a message component"
    );
    const messageEl = document.querySelector('.o_Message');
    assert.strictEqual(
        messageEl.dataset.messageLocalId,
        messaging.models['Message'].findFromIdentifyingData({ id: 100 }).localId,
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
        '/web/image/res.partner/7/avatar_128',
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
    const mailChannelId1 = pyEnv['mail.channel'].create();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: 'Someone', partner_share: true });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: 'not empty',
        message_type: 'email',
        model: 'mail.channel',
        res_id: mailChannelId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'email',
        res_partner_id: resPartnerId1,
    });
    const { click, createThreadViewComponent, messaging } = await start();
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    const threadViewer = messaging.models['ThreadViewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: link(thread),
    });
    await createThreadViewComponent(threadViewer.threadView);

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
        '.o_NotificationPopover',
        "notification popover should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationPopover_notificationIcon',
        "popover should have one icon"
    );
    assert.hasClass(
        document.querySelector('.o_NotificationPopover_notificationIcon'),
        'fa-check',
        "popover should have the sent icon"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationPopover_notificationPartnerName',
        "popover should have the partner name"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationPopover_notificationPartnerName').textContent.trim(),
        "Someone",
        "partner name should be correct"
    );
});

QUnit.test('Notification Error', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Someone", partner_share: true });
    const mailChannelId1 = pyEnv['mail.channel'].create();
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: 'not empty',
        message_type: 'email',
        model: 'mail.channel',
        res_id: mailChannelId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'exception',
        notification_type: 'email',
        res_partner_id: resPartnerId1,
    });
    const openResendActionDef = makeDeferred();
    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action,
            'mail.mail_resend_message_action',
            "action should be the one to resend email"
        );
        assert.strictEqual(
            payload.options.additional_context.mail_message_to_resend,
            mailMessageId1,
            "action should have correct message id"
        );
        openResendActionDef.resolve();
    });
    const { createThreadViewComponent, messaging } = await start({ env: { bus } });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    const threadViewer = messaging.models['ThreadViewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: link(thread),
    });
    await createThreadViewComponent(threadViewer.threadView);

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
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: "Recipient" });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: 'chat',
    });
    const { createThreadViewComponent, messaging, widget } = await start();
    const currentPartner = messaging.models['Partner'].insert({
        id: messaging.currentPartner.id,
        display_name: "Demo User",
    });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    const threadViewer = messaging.models['ThreadViewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: link(thread),
    });
    messaging.models['Message'].create({
        author: link(currentPartner),
        body: "<p>Test</p>",
        id: 100,
        originThread: link(thread),
    });

    await createThreadViewComponent(threadViewer.threadView);

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

    // Simulate received channel fetched notification
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/fetched',
            payload: {
                channel_id: mailChannelId1,
                last_message_id: 100,
                partner_id: resPartnerId1,
            },
    }]);
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
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: "Recipient" });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: 'chat',
    });
    const { createThreadViewComponent, messaging, widget } = await start();
    const currentPartner = messaging.models['Partner'].insert({
        id: messaging.currentPartner.id,
        display_name: "Demo User",
    });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    const threadViewer = messaging.models['ThreadViewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: link(thread),
    });
    messaging.models['Message'].create({
        author: link(currentPartner),
        body: "<p>Test</p>",
        id: 100,
        originThread: link(thread),
    });
    await createThreadViewComponent(threadViewer.threadView);

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

    // Simulate received channel seen notification
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/seen',
            payload: {
                channel_id: mailChannelId1,
                last_message_id: 100,
                partner_id: resPartnerId1,
            },
        }]);
    });
    assert.containsN(
        document.body,
        '.o_MessageSeenIndicator_icon',
        2,
        "message seen indicator component should contain two checks (V) as message is seen"
    );
});

QUnit.test("'channel_fetch' notification then 'channel_seen' received  are correctly handled", async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: "Recipient" });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: 'chat',
    });
    const { createThreadViewComponent, messaging, widget } = await start();
    const currentPartner = messaging.models['Partner'].insert({
        id: messaging.currentPartner.id,
        display_name: "Demo User",
    });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    const threadViewer = messaging.models['ThreadViewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: link(thread),
    });
    messaging.models['Message'].create({
        author: link(currentPartner),
        body: "<p>Test</p>",
        id: 100,
        originThread: link(thread),
    });
    await createThreadViewComponent(threadViewer.threadView);

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

    // Simulate received channel fetched notification
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/fetched',
            payload: {
                channel_id: mailChannelId1,
                last_message_id: 100,
                partner_id: resPartnerId1,
            }
        }]);
    });
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator_icon',
        "message seen indicator component should only contain one check (V) as message is just received"
    );

    // Simulate received channel seen notification
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/seen',
            payload: {
                channel_id: mailChannelId1,
                last_message_id: 100,
                partner_id: resPartnerId1,
            },
        }]);
    });
    assert.containsN(
        document.body,
        '.o_MessageSeenIndicator_icon',
        2,
        "message seen indicator component should contain two checks (V) as message is now seen"
    );
});

QUnit.test('do not show messaging seen indicator if not authored by me', async function (assert) {
    assert.expect(2);

    const { createThreadViewComponent, messaging } = await start();
    const author = messaging.models['Partner'].create({
        id: 100,
        display_name: "Demo User"
    });
    const thread = messaging.models['Thread'].create({
        channel_type: 'chat',
        id: 11,
        partnerSeenInfos: insertAndReplace([
            {
                lastFetchedMessage: insert({ id: 100 }),
                partner: replace(messaging.currentPartner),
            },
            {
                lastFetchedMessage: insert({ id: 100 }),
                partner: replace(author),
            },
        ]),
        model: 'mail.channel',
    });
    const threadViewer = messaging.models['ThreadViewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: link(thread),
    });
    messaging.models['Message'].insert({
        author: link(author),
        body: "<p>Test</p>",
        id: 100,
        originThread: link(thread),
    });
    await createThreadViewComponent(threadViewer.threadView);

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsNone(
        document.body,
        '.o_Message_seenIndicator',
        "message component should not have any message seen indicator"
    );
});

QUnit.test('do not show messaging seen indicator if before last seen by all message', async function (assert) {
    assert.expect(3);

    const { env, messaging, widget } = await start();
    const currentPartner = messaging.models['Partner'].insert({
        id: messaging.currentPartner.id,
        display_name: "Demo User",
    });
    const thread = messaging.models['Thread'].create({
        channel_type: 'chat',
        id: 11,
        messageSeenIndicators: insertAndReplace({
            message: insertAndReplace({ id: 99 }),
        }),
        model: 'mail.channel',
    });
    const threadViewer = messaging.models['ThreadViewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: link(thread),
    });
    const lastSeenMessage = messaging.models['Message'].create({
        author: link(currentPartner),
        body: "<p>You already saw me</p>",
        id: 100,
        originThread: link(thread),
    });
    messaging.models['Message'].insert({
        author: link(currentPartner),
        body: "<p>Test</p>",
        id: 99,
        originThread: link(thread),
    });
    messaging.models['ThreadPartnerSeenInfo'].insert([
        {
            lastSeenMessage: link(lastSeenMessage),
            partner: replace(messaging.currentPartner),
            thread: replace(thread),
        },
        {
            lastSeenMessage: link(lastSeenMessage),
            partner: insertAndReplace({ id: 100 }),
            thread: replace(thread),
        },
    ]);
     await createRootMessagingComponent(env, "Message", {
        props: { localId: threadViewer.threadView.messageViews[0].localId },
        target: widget.el,
    });

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
    assert.containsNone(
        document.body,
        '.o_MessageSeenIndicator_icon',
        "message component should not have any check (V)"
    );
});

QUnit.test('only show messaging seen indicator if authored by me, after last seen by all message', async function (assert) {
    assert.expect(3);

    const { createThreadViewComponent, messaging } = await start();
    const currentPartner = messaging.models['Partner'].insert({
        id: messaging.currentPartner.id,
        display_name: "Demo User"
    });
    const thread = messaging.models['Thread'].create({
        channel_type: 'chat',
        id: 11,
        partnerSeenInfos: insertAndReplace([
            {
                lastSeenMessage: insert({ id: 100 }),
                partner: replace(messaging.currentPartner),
            },
            {
                lastFetchedMessage: insert({ id: 100 }),
                lastSeenMessage: insert({ id: 99 }),
                partner: insertAndReplace({ id: 100 }),
            },
        ]),
        messageSeenIndicators: insertAndReplace({
            message: insertAndReplace({ id: 100 }),
        }),
        model: 'mail.channel',
    });
    const threadViewer = messaging.models['ThreadViewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: link(thread),
    });
    messaging.models['Message'].insert({
        author: link(currentPartner),
        body: "<p>Test</p>",
        id: 100,
        originThread: link(thread),
    });
    await createThreadViewComponent(threadViewer.threadView);

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

    const { click, createMessageComponent, messaging } = await start({ hasDialog: true });
    const message = messaging.models['Message'].create({
        attachments: insertAndReplace({
            filename: "BLAH.jpg",
            id: 10,
            name: "BLAH",
            mimetype: 'image/jpeg',
        }),
        author: link(messaging.currentPartner),
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);

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

    const { createMessageComponent, messaging } = await start();
    const message = messaging.models['Message'].create({
        attachments: insertAndReplace({
            filename: "BLAH.jpg",
            id: 10,
            name: "BLAH",
            mimetype: 'image/jpeg',
            originThread: insertAndReplace({
                id: 11,
                model: 'mail.channel',
            }),
        }),
        author: insert({ id: 11, display_name: "Guy" }),
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);

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

QUnit.test('subtype description should be displayed if it is different than body', async function (assert) {
    assert.expect(2);

    const { createMessageComponent, messaging } = await start();
    const message = messaging.models['Message'].create({
        body: "<p>Hello</p>",
        id: 100,
        subtype_description: 'Bonjour',
    });
    await createMessageComponent(message);
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

    const { createMessageComponent, messaging } = await start();
    const message = messaging.models['Message'].create({
        body: "<p>Hello</p>",
        id: 100,
        subtype_description: 'hello',
    });
    await createMessageComponent(message);
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

    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.strictEqual(
            payload.action.type,
            'ir.actions.act_window',
            "action should open view"
        );
        assert.strictEqual(
            payload.action.res_model,
            'some.model',
            "action should open view on 'some.model' model"
        );
        assert.strictEqual(
            payload.action.res_id,
            250,
            "action should open view on 250"
        );
        assert.step('do-action:openFormView_some.model_250');
    });
    const { createMessageComponent, messaging } = await start({ env: { bus } });
    const message = messaging.models['Message'].create({
        body: `<p><a href="#" data-oe-id="250" data-oe-model="some.model">some.model_250</a></p>`,
        id: 100,
    });
    await createMessageComponent(message);
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

QUnit.test('chat with author should be opened after clicking on his avatar', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create();
    pyEnv['res.users'].create({ partner_id: resPartnerId1 });
    const { click, createMessageComponent, messaging } = await start({ hasChatWindow: true });
    const message = messaging.models['Message'].create({
        author: insert({ id: resPartnerId1 }),
        id: 10,
    });
    await createMessageComponent(message);
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
        message.author.id.toString(),
        "chat with author should be opened after clicking on his avatar"
    );
});

QUnit.test('chat with author should be opened after clicking on his im status icon', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create();
    pyEnv['res.users'].create({ partner_id: resPartnerId1 });
    const { click, createMessageComponent, messaging } = await start({ hasChatWindow: true });
    const message = messaging.models['Message'].create({
        author: insert({ id: resPartnerId1, im_status: 'online' }),
        id: 10,
    });
    await createMessageComponent(message);
    assert.containsOnce(
        document.body,
        '.o_Message_partnerImStatusIcon',
        "message should have the author im status icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_partnerImStatusIcon'),
        'o-has-open-chat',
        "author im status icon should have the open chat style"
    );

    await click('.o_Message_partnerImStatusIcon');
    assert.containsOnce(
        document.body,
        '.o_ChatWindow_thread',
        "chat window with thread should be opened after clicking on author im status icon"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindow_thread').dataset.correspondentId,
        message.author.id.toString(),
        "chat with author should be opened after clicking on his im status icon"
    );
});

QUnit.test('open chat with author on avatar click should be disabled when currently chatting with the author', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create();
    pyEnv['res.users'].create({ partner_id: resPartnerId1 });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: 'chat',
        public: 'private',
    });
    pyEnv['mail.message'].create({
        author_id: resPartnerId1,
        body: 'not empty',
        model: 'mail.channel',
        res_id: mailChannelId1,
    });
    const { createThreadViewComponent, messaging } = await start({ hasChatWindow: true });
    const correspondent = messaging.models['Partner'].insert({ id: resPartnerId1 });
    const thread = await correspondent.getChat();
    const threadViewer = messaging.models['ThreadViewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: link(thread),
    });
    await createThreadViewComponent(threadViewer.threadView);
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

QUnit.test('message should not be considered as "clicked" after clicking on its author name', async function (assert) {
    assert.expect(1);

    const { createMessageComponent, messaging } = await start();
    const message = messaging.models['Message'].create({
        author: [['insert', { id: 7, display_name: "Demo User" }]],
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);
    document.querySelector(`.o_Message_authorName`).click();
    await nextAnimationFrame();
    assert.doesNotHaveClass(
        document.querySelector(`.o_Message`),
        'o-clicked',
        "message should not be considered as 'clicked' after clicking on its author name"
    );
});

QUnit.test('message should not be considered as "clicked" after clicking on its author avatar', async function (assert) {
    assert.expect(1);

    const { createMessageComponent, messaging } = await start();
    const message = messaging.models['Message'].create({
        author: [['insert', { id: 7, display_name: "Demo User" }]],
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);
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
    const mailChannelId1 = pyEnv['mail.channel'].create();
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: 'not empty',
        model: 'mail.channel',
        res_id: mailChannelId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'exception',
        notification_type: 'email',
    });
    const { createThreadViewComponent, messaging } = await start();
    const threadViewer = messaging.models['ThreadViewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: insert({
            id: mailChannelId1,
            model: 'mail.channel',
        }),
    });
    await createThreadViewComponent(threadViewer.threadView);
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
