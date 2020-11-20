odoo.define('mail/static/src/components/message/message_tests.js', function (require) {
'use strict';

const components = {
    Message: require('mail/static/src/components/message/message.js'),
};
const { makeDeferred } = require('mail/static/src/utils/deferred/deferred.js');
const {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    nextAnimationFrame,
    start,
} = require('mail/static/src/utils/test_utils.js');

const Bus = require('web.Bus');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('message', {}, function () {
QUnit.module('message_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createMessageComponent = async (message, otherProps) => {
            const props = Object.assign({ messageLocalId: message.localId }, otherProps);
            await createRootComponent(this, components.Message, {
                props,
                target: this.widget.el,
            });
        };

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('basic rendering', async function (assert) {
    assert.expect(12);

    await this.start();
    const message = this.env.models['mail.message'].create({
        author: [['insert', { id: 7, display_name: "Demo User" }]],
        body: "<p>Test</p>",
        id: 100,
    });
    await this.createMessageComponent(message);
    assert.strictEqual(
        document.querySelectorAll('.o_Message').length,
        1,
        "should display a message component"
    );
    const messageEl = document.querySelector('.o_Message');
    assert.strictEqual(
        messageEl.dataset.messageLocalId,
        this.env.models['mail.message'].find(message => message.id === 100).localId,
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
        '/web/image/res.partner/7/image_128',
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
    assert.strictEqual(
        messageEl.querySelectorAll(`:scope .o_Message_commands`).length,
        1,
        "message should display list of commands"
    );
    assert.strictEqual(
        messageEl.querySelectorAll(`:scope .o_Message_content`).length,
        1,
        "message should display the content"
    );
    assert.strictEqual(
        messageEl.querySelector(`:scope .o_Message_content`).innerHTML,
        "<p>Test</p>",
        "message should display the correct content"
    );
});

QUnit.test('moderation: as author, moderated channel with pending moderation message', async function (assert) {
    assert.expect(1);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        id: 20,
        model: 'mail.channel',
    });
    const message = this.env.models['mail.message'].create({
        author: [['insert', { id: 1, display_name: "Admin" }]],
        body: "<p>Test</p>",
        id: 100,
        moderation_status: 'pending_moderation',
        originThread: [['link', thread]],
    });
    await this.createMessageComponent(message);

    assert.strictEqual(
        document.querySelectorAll(`.o_Message_moderationPending.o-author`).length,
        1,
        "should have the message pending moderation"
    );
});

QUnit.test('moderation: as moderator, moderated channel with pending moderation message', async function (assert) {
    assert.expect(9);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        id: 20,
        model: 'mail.channel',
        moderators: [['link', this.env.messaging.currentPartner]],
    });
    const message = this.env.models['mail.message'].create({
        author: [['insert', { id: 7, display_name: "Demo User" }]],
        body: "<p>Test</p>",
        id: 100,
        moderation_status: 'pending_moderation',
        originThread: [['link', thread]],
    });
    await this.createMessageComponent(message);
    const messageEl = document.querySelector('.o_Message');
    assert.ok(messageEl, "should display a message");
    assert.containsOnce(messageEl, `.o_Message_moderationSubHeader`,
        "should have the message pending moderation"
    );
    assert.containsNone(messageEl, `.o_Message_checkbox`,
        "should not have the moderation checkbox by default"
    );
    assert.containsN(messageEl, '.o_Message_moderationAction', 5,
        "there should be 5 contextual moderation decisions next to the message"
    );
    assert.containsOnce(messageEl, '.o_Message_moderationAction.o-accept',
        "there should be a contextual moderation decision to accept the message"
    );
    assert.containsOnce(messageEl, '.o_Message_moderationAction.o-reject',
        "there should be a contextual moderation decision to reject the message"
    );
    assert.containsOnce(messageEl, '.o_Message_moderationAction.o-discard',
        "there should be a contextual moderation decision to discard the message"
    );
    assert.containsOnce(messageEl, '.o_Message_moderationAction.o-allow',
        "there should be a contextual moderation decision to allow the user of the message)"
    );
    assert.containsOnce(messageEl, '.o_Message_moderationAction.o-ban',
        "there should be a contextual moderation decision to ban the user of the message"
    );
    // The actions are tested as part of discuss tests.
});

QUnit.test('Notification Sent', async function (assert) {
    assert.expect(9);

    await this.start();
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['create', {
            id: 11,
            model: 'mail.channel',
        }]],
    });
    const message = this.env.models['mail.message'].create({
        id: 10,
        message_type: 'email',
        notifications: [['insert', {
            id: 11,
            notification_status: 'sent',
            notification_type: 'email',
            partner: [['insert', { id: 12, name: "Someone" }]],
        }]],
        originThread: [['link', threadViewer.thread]],
    });
    await this.createMessageComponent(message, {
        threadViewLocalId: threadViewer.threadView.localId
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

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconClickable').click();
    });
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
            10,
            "action should have correct message id"
        );
        openResendActionDef.resolve();
    });

    await this.start({ env: { bus } });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['create', {
            id: 11,
            model: 'mail.channel',
        }]],
    });
    const message = this.env.models['mail.message'].create({
        id: 10,
        message_type: 'email',
        notifications: [['insert', {
            id: 11,
            notification_status: 'exception',
            notification_type: 'email',
        }]],
        originThread: [['link', threadViewer.thread]],
    });
    await this.createMessageComponent(message, {
        threadViewLocalId: threadViewer.threadView.localId
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

    await this.start();
    const currentPartner = this.env.models['mail.partner'].insert({
        id: this.env.messaging.currentPartner.id,
        display_name: "Demo User",
    });
    const thread = this.env.models['mail.thread'].create({
        channel_type: 'chat',
        id: 11,
        members: [
            [['link', currentPartner]],
            [['insert', { id: 11, display_name: "Recipient" }]]
        ],
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    const message = this.env.models['mail.message'].create({
        author: [['link', currentPartner]],
        body: "<p>Test</p>",
        id: 100,
        originThread: [['link', thread]],
    });

    await this.createMessageComponent(message, {
        threadViewLocalId: threadViewer.threadView.localId,
    });

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
    const notifications = [
        [['myDB', 'mail.channel', 11], {
            info: 'channel_fetched',
            last_message_id: 100,
            partner_id: 11,
        }],
    ];
    await afterNextRender(() => {
        this.widget.call('bus_service', 'trigger', 'notification', notifications);
    });

    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator_icon',
        "message seen indicator component should only contain one check (V) as message is just received"
    );
});

QUnit.test("'channel_seen' notification received is correctly handled", async function (assert) {
    assert.expect(3);

    await this.start();
    const currentPartner = this.env.models['mail.partner'].insert({
        id: this.env.messaging.currentPartner.id,
        display_name: "Demo User",
    });
    const thread = this.env.models['mail.thread'].create({
        channel_type: 'chat',
        id: 11,
        members: [
            [['link', currentPartner]],
            [['insert', { id: 11, display_name: "Recipient" }]]
        ],
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    const message = this.env.models['mail.message'].create({
        author: [['link', currentPartner]],
        body: "<p>Test</p>",
        id: 100,
        originThread: [['link', thread]],
    });
    await this.createMessageComponent(message, {
        threadViewLocalId: threadViewer.threadView.localId,
    });

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
    const notifications = [
        [['myDB', 'mail.channel', 11], {
            info: 'channel_seen',
            last_message_id: 100,
            partner_id: 11,
        }],
    ];
    await afterNextRender(() => {
        this.widget.call('bus_service', 'trigger', 'notification', notifications);
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

    await this.start();
    const currentPartner = this.env.models['mail.partner'].insert({
        id: this.env.messaging.currentPartner.id,
        display_name: "Demo User",
    });
    const thread = this.env.models['mail.thread'].create({
        channel_type: 'chat',
        id: 11,
        members: [
            [['link', currentPartner]],
            [['insert', { id: 11, display_name: "Recipient" }]]
        ],
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    const message = this.env.models['mail.message'].create({
        author: [['link', currentPartner]],
        body: "<p>Test</p>",
        id: 100,
        originThread: [['link', thread]],
    });
    await this.createMessageComponent(message, {
        threadViewLocalId: threadViewer.threadView.localId,
    });

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
    let notifications = [
        [['myDB', 'mail.channel', 11], {
            info: 'channel_fetched',
            last_message_id: 100,
            partner_id: 11,
        }],
    ];
    await afterNextRender(() => {
        this.widget.call('bus_service', 'trigger', 'notification', notifications);
    });
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator_icon',
        "message seen indicator component should only contain one check (V) as message is just received"
    );

    // Simulate received channel seen notification
    notifications = [
        [['myDB', 'mail.channel', 11], {
            info: 'channel_seen',
            last_message_id: 100,
            partner_id: 11,
        }],
    ];
    await afterNextRender(() => {
        this.widget.call('bus_service', 'trigger', 'notification', notifications);
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

    await this.start();
    const author = this.env.models['mail.partner'].create({
        id: 100,
        display_name: "Demo User"
    });
    const thread = this.env.models['mail.thread'].create({
        channel_type: 'chat',
        id: 11,
        partnerSeenInfos: [['create', [
            {
                channelId: 11,
                lastFetchedMessage: [['insert', { id: 100 }]],
                partnerId: this.env.messaging.currentPartner.id,
            },
            {
                channelId: 11,
                lastFetchedMessage: [['insert', { id: 100 }]],
                partnerId: author.id,
            },
        ]]],
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    const message = this.env.models['mail.message'].insert({
        author: [['link', author]],
        body: "<p>Test</p>",
        id: 100,
        originThread: [['link', thread]],
    });
    await this.createMessageComponent(message, { threadViewLocalId: threadViewer.threadView.localId });

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

    await this.start();
    const currentPartner = this.env.models['mail.partner'].insert({
        id: this.env.messaging.currentPartner.id,
        display_name: "Demo User",
    });
    const thread = this.env.models['mail.thread'].create({
        channel_type: 'chat',
        id: 11,
        messageSeenIndicators: [['insert', {
            channelId: 11,
            messageId: 99,
        }]],
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    const lastSeenMessage = this.env.models['mail.message'].create({
        author: [['link', currentPartner]],
        body: "<p>You already saw me</p>",
        id: 100,
        originThread: [['link', thread]],
    });
    const message = this.env.models['mail.message'].insert({
        author: [['link', currentPartner]],
        body: "<p>Test</p>",
        id: 99,
        originThread: [['link', thread]],
    });
    thread.update({
       partnerSeenInfos: [['create', [
            {
                channelId: 11,
                lastSeenMessage: [['link', lastSeenMessage]],
                partnerId: this.env.messaging.currentPartner.id,
            },
            {
                channelId: 11,
                lastSeenMessage: [['link', lastSeenMessage]],
                partnerId: 100,
            },
        ]]],
    });
    await this.createMessageComponent(message, {
        threadViewLocalId: threadViewer.threadView.localId,
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

    await this.start();
    const currentPartner = this.env.models['mail.partner'].insert({
        id: this.env.messaging.currentPartner.id,
        display_name: "Demo User"
    });
    const thread = this.env.models['mail.thread'].create({
        channel_type: 'chat',
        id: 11,
        partnerSeenInfos: [['create', [
            {
                channelId: 11,
                lastSeenMessage: [['insert', { id: 100 }]],
                partnerId: this.env.messaging.currentPartner.id,
            },
            {
                channelId: 11,
                lastFetchedMessage: [['insert', { id: 100 }]],
                lastSeenMessage: [['insert', { id: 99 }]],
                partnerId: 100,
            },
        ]]],
        messageSeenIndicators: [['insert', {
            channelId: 11,
            messageId: 100,
        }]],
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    const message = this.env.models['mail.message'].insert({
        author: [['link', currentPartner]],
        body: "<p>Test</p>",
        id: 100,
        originThread: [['link', thread]],
    });
    await this.createMessageComponent(message, {
        threadViewLocalId: threadViewer.threadView.localId,
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
    assert.containsN(
        document.body,
        '.o_MessageSeenIndicator_icon',
        1,
        "message component should have one check (V) because the message was fetched by everyone but no other member than author has seen the message"
    );
});

QUnit.test('allow attachment delete on authored message', async function (assert) {
    assert.expect(5);

    await this.start();
    const message = this.env.models['mail.message'].create({
        attachments: [['insert-and-replace', {
            filename: "BLAH.jpg",
            id: 10,
            name: "BLAH",
        }]],
        author: [['link', this.env.messaging.currentPartner]],
        body: "<p>Test</p>",
        id: 100,
    });
    await this.createMessageComponent(message);

    assert.containsOnce(
        document.body,
        '.o_Attachment',
        "should have an attachment",
    );
    assert.containsOnce(
        document.body,
        '.o_Attachment_asideItemUnlink',
        "should have delete attachment button"
    );

    await afterNextRender(() => document.querySelector('.o_Attachment_asideItemUnlink').click());
    assert.containsOnce(
        document.body,
        '.o_AttachmentDeleteConfirmDialog',
        "An attachment delete confirmation dialog should have been opened"
    );
    assert.strictEqual(
        document.querySelector('.o_AttachmentDeleteConfirmDialog_mainText').textContent,
        `Do you really want to delete "BLAH"?`,
        "Confirmation dialog should contain the attachment delete confirmation text"
    );

    await afterNextRender(() =>
        document.querySelector('.o_AttachmentDeleteConfirmDialog_confirmButton').click()
    );
    assert.containsNone(
        document.body,
        '.o_Attachment',
        "should no longer have an attachment",
    );
});

QUnit.test('prevent attachment delete on non-authored message', async function (assert) {
    assert.expect(2);

    await this.start();
    const message = this.env.models['mail.message'].create({
        attachments: [['insert-and-replace', {
            filename: "BLAH.jpg",
            id: 10,
            name: "BLAH",
        }]],
        author: [['insert', { id: 11, display_name: "Guy" }]],
        body: "<p>Test</p>",
        id: 100,
    });
    await this.createMessageComponent(message);

    assert.containsOnce(
        document.body,
        '.o_Attachment',
        "should have an attachment",
    );
    assert.containsNone(
        document.body,
        '.o_Attachment_asideItemUnlink',
        "delete attachment button should not be printed"
    );
});

QUnit.test('subtype description should be displayed if it is different than body', async function (assert) {
    assert.expect(2);

    await this.start();
    const message = this.env.models['mail.message'].create({
        body: "<p>Hello</p>",
        id: 100,
        subtype_description: 'Bonjour',
    });
    await this.createMessageComponent(message);
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

    await this.start();
    const message = this.env.models['mail.message'].create({
        body: "<p>Hello</p>",
        id: 100,
        subtype_description: 'hello',
    });
    await this.createMessageComponent(message);
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
    await this.start({ env: { bus } });
    const message = this.env.models['mail.message'].create({
        body: `<p><a href="#" data-oe-id="250" data-oe-model="some.model">some.model_250</a></p>`,
        id: 100,
    });
    await this.createMessageComponent(message);
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

    this.data['res.partner'].records.push({ id: 10 });
    this.data['res.users'].records.push({ partner_id: 10 });
    await this.start({
        hasChatWindow: true,
    });
    const message = this.env.models['mail.message'].create({
        author: [['insert', { id: 10 }]],
        id: 10,
    });
    await this.createMessageComponent(message);
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

    await afterNextRender(() =>
        document.querySelector('.o_Message_authorAvatar').click()
    );
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

    this.data['res.partner'].records.push({ id: 10 });
    this.data['res.users'].records.push({ partner_id: 10 });
    await this.start({
        hasChatWindow: true,
    });
    const message = this.env.models['mail.message'].create({
        author: [['insert', { id: 10, im_status: 'online' }]],
        id: 10,
    });
    await this.createMessageComponent(message);
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

    await afterNextRender(() =>
        document.querySelector('.o_Message_partnerImStatusIcon').click()
    );
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

    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        members: [this.data.currentPartnerId, 10],
        public: 'private',
    });
    this.data['res.partner'].records.push({ id: 10 });
    this.data['res.users'].records.push({ partner_id: 10 });
    await this.start({
        hasChatWindow: true,
    });
    const correspondent = this.env.models['mail.partner'].insert({ id: 10 });
    const message = this.env.models['mail.message'].create({
        author: [['link', correspondent]],
        id: 10,
    });
    const thread = await correspondent.getChat();
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createMessageComponent(message, {
        threadViewLocalId: threadViewer.threadView.localId,
    });
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

QUnit.test('basic rendering of tracking value (float type)', async function (assert) {
    assert.expect(8);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        tracking_value_ids: [{
            changed_field: "Total",
            field_type: "float",
            id: 6,
            new_value: 45.67,
            old_value: 12.3,
        }],
    });
    await this.createMessageComponent(message);
    assert.containsOnce(
        document.body,
        '.o_Message_trackingValue',
        "should display a tracking value"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_trackingValueFieldName',
        "should display the name of the tracked field"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValueFieldName').textContent,
        "Total:",
        "should display the correct tracked field name (Total)",
    );
    assert.containsOnce(
        document.body,
        '.o_Message_trackingValueOldValue',
        "should display the old value"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValueOldValue').textContent,
        "12.3",
        "should display the correct old value (12.3)",
    );
    assert.containsOnce(
        document.body,
        '.o_Message_trackingValueSeparator',
        "should display the separator"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_trackingValueNewValue',
        "should display the new value"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValueNewValue').textContent,
        "45.67",
        "should display the correct new value (45.67)",
    );
});

QUnit.test('rendering of tracked field with change of value from non-0 to 0', async function (assert) {
    assert.expect(1);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        tracking_value_ids: [{
            changed_field: "Total",
            field_type: "float",
            id: 6,
            new_value: 0,
            old_value: 1,
        }],
    });
    await this.createMessageComponent(message);
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Total:10",
        "should display the correct content of tracked field with change of value from non-0 to 0 (Total: 1 -> 0)"
    );
});

QUnit.test('rendering of tracked field with change of value from 0 to non-0', async function (assert) {
    assert.expect(1);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        tracking_value_ids: [{
            changed_field: "Total",
            field_type: "float",
            id: 6,
            new_value: 1,
            old_value: 0,
        }],
    });
    await this.createMessageComponent(message);
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Total:01",
        "should display the correct content of tracked field with change of value from 0 to non-0 (Total: 0 -> 1)"
    );
});

QUnit.test('rendering of tracked field with change of value from true to false', async function (assert) {
    assert.expect(1);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        tracking_value_ids: [{
            changed_field: "Is Ready",
            field_type: "boolean",
            id: 6,
            new_value: false,
            old_value: true,
        }],
    });
    await this.createMessageComponent(message);
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Is Ready:truefalse",
        "should display the correct content of tracked field with change of value from true to false (Is Ready: true -> false)"
    );
});

QUnit.test('rendering of tracked field with change of value from false to true', async function (assert) {
    assert.expect(1);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        tracking_value_ids: [{
            changed_field: "Is Ready",
            field_type: "boolean",
            id: 6,
            new_value: true,
            old_value: false,
        }],
    });
    await this.createMessageComponent(message);
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Is Ready:falsetrue",
        "should display the correct content of tracked field with change of value from false to true (Is Ready: false -> true)"
    );
});

QUnit.test('rendering of tracked field with change of value from string to empty', async function (assert) {
    assert.expect(1);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        tracking_value_ids: [{
            changed_field: "Name",
            field_type: "char",
            id: 6,
            new_value: "",
            old_value: "Marc",
        }],
    });
    await this.createMessageComponent(message);
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Name:Marc",
        "should display the correct content of tracked field with change of value from string to empty (Total: Marc ->)"
    );
});

QUnit.test('rendering of tracked field with change of value from empty to string', async function (assert) {
    assert.expect(1);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        tracking_value_ids: [{
            changed_field: "Name",
            field_type: "char",
            id: 6,
            new_value: "Marc",
            old_value: "",
        }],
    });
    await this.createMessageComponent(message);
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Name:Marc",
        "should display the correct content of tracked field with change of value from empty to string (Total: -> Marc)"
    );
});

});
});
});

});
