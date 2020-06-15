odoo.define('mail/static/src/components/message/message_tests.js', function (require) {
'use strict';

const components = {
    Message: require('mail/static/src/components/message/message.js'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

const Bus = require('web.Bus');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('message', {}, function () {
QUnit.module('message_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createMessageComponent = async (message, otherProps) => {
            const MessageComponent = components.Message;
            MessageComponent.env = this.env;
            this.component = new MessageComponent(null, Object.assign({
                messageLocalId: message.localId,
            }, otherProps));
            await afterNextRender(() => this.component.mount(this.widget.el));
        };

        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.component) {
            this.component.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.env = undefined;
        delete components.Message.env;
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
    assert.strictEqual(messageEl.querySelector(`:scope .o_Message_content`).innerHTML,
        "<p>Test</p>",
        "message should display the correct content"
    );
});

QUnit.test('delete attachment linked to message', async function (assert) {
    assert.expect(1);

    await this.start();
    const message = this.env.models['mail.message'].create({
        attachments: [['insert-and-replace', {
            filename: "BLAH.jpg",
            id: 10,
            name: "BLAH",
        }]],
        author: [['insert', { id: 7, display_name: "Demo User" }]],
        body: "<p>Test</p>",
        id: 100,
    });
    await this.createMessageComponent(message);
    await afterNextRender(() => document.querySelector('.o_Attachment_asideItemUnlink').click());
    assert.notOk(this.env.models['mail.attachment'].find(attachment => attachment.id === 10));
});

QUnit.test('moderation: moderated channel with pending moderation message (author)', async function (assert) {
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
        threadCaches: [['link', thread.mainCache]],
    });
    await this.createMessageComponent(message);

    assert.strictEqual(
        document.querySelectorAll(`.o_Message_moderationPending.o-author`).length,
        1,
        "should have the message pending moderation"
    );
});

QUnit.test('moderation: moderated channel with pending moderation message (moderator)', async function (assert) {
    assert.expect(9);

    Object.assign(this.data.initMessaging, {
        moderation_channel_ids: [20],
    });
    await this.start();
    const thread = this.env.models['mail.thread'].create({
        id: 20,
        model: 'mail.channel',
    });
    const message = this.env.models['mail.message'].create({
        author: [['insert', { id: 7, display_name: "Demo User" }]],
        body: "<p>Test</p>",
        id: 100,
        moderation_status: 'pending_moderation',
        originThread: [['link', thread]],
        threadCaches: [['link', thread.mainCache]],
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
    const message = this.env.models['mail.message'].create({
        id: 10,
        message_type: 'email',
        notifications: [['insert', {
            id: 11,
            notification_status: 'sent',
            notification_type: 'email',
            partner: [['insert', { id: 12, name: "Someone" }]],
        }]],
    });
    await this.createMessageComponent(message);

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconContainer',
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
        document.querySelector('.o_Message_notificationIconContainer').click();
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
    });

    await this.start({ env: { bus } });
    const message = this.env.models['mail.message'].create({
        id: 10,
        message_type: 'email',
        notifications: [['insert', {
            id: 11,
            notification_status: 'exception',
            notification_type: 'email',
        }]],
    });
    await this.createMessageComponent(message);

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconContainer',
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

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconContainer').click();
    });
    assert.verifySteps(
        ['do_action'],
        "should do an action to display the resend email dialog"
    );
});

QUnit.test("'channel_fetch' notification received is correctly handled", async function (assert) {
    assert.expect(3);

    await this.start();
    const currentPartner = this.env.models['mail.partner'].create({
        id: this.env.session.partner_id,
        display_name: "Demo User",
    });
    const thread = this.env.models['mail.thread'].create({
        id: 11,
        members: [
            [['link', currentPartner]],
            [['insert', { id: 11, display_name: "Recipient" }]]
        ],
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({ thread: [['link', thread]] });
    const message = this.env.models['mail.message'].create({
        author: [['link', currentPartner]],
        body: "<p>Test</p>",
        id: 100,
        threadCaches: [['link', thread.mainCache]],
    });

    await this.createMessageComponent(message, { threadViewerLocalId: threadViewer.localId });

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
    const currentPartner = this.env.models['mail.partner'].create({
        id: this.env.session.partner_id,
        display_name: "Demo User",
    });
    const thread = this.env.models['mail.thread'].create({
        id: 11,
        members: [
            [['link', currentPartner]],
            [['insert', { id: 11, display_name: "Recipient" }]]
        ],
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({ thread: [['link', thread]] });
    const message = this.env.models['mail.message'].create({
        author: [['link', currentPartner]],
        body: "<p>Test</p>",
        id: 100,
        threadCaches: [['link', thread.mainCache]],
    });
    await this.createMessageComponent(message, { threadViewerLocalId: threadViewer.localId });

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
    const currentPartner = this.env.models['mail.partner'].create({
        id: this.env.session.partner_id,
        display_name: "Demo User",
    });
    const thread = this.env.models['mail.thread'].create({
        id: 11,
        members: [
            [['link', currentPartner]],
            [['insert', { id: 11, display_name: "Recipient" }]]
        ],
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({ thread: [['link', thread]] });
    const message = this.env.models['mail.message'].create({
        author: [['link', currentPartner]],
        body: "<p>Test</p>",
        id: 100,
        threadCaches: [['link', thread.mainCache]],
    });
    await this.createMessageComponent(message, { threadViewerLocalId: threadViewer.localId });

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
        id: 11,
        partnerSeenInfos: [['create', [
            {
                lastFetchedMessage: [['insert', {id: 100}]],
                partner: [['insert', {id: this.env.session.partner_id}]],
            },
            {
                lastFetchedMessage: [['insert', {id: 100}]],
                partner: [['link', author]],
            },
        ]]],
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({ thread: [['link', thread]] });
    const message = this.env.models['mail.message'].create({
        author: [['link', author]],
        body: "<p>Test</p>",
        id: 100,
        threadCaches: [['link', thread.mainCache]],
    });
    await this.createMessageComponent(message, { threadViewerLocalId: threadViewer.localId });

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
    const currentPartner = this.env.models['mail.partner'].create({
        id: this.env.session.partner_id,
        display_name: "Demo User",
    });
    const thread = this.env.models['mail.thread'].create({
        id: 11,
        messageSeenIndicators: [['insert', {
            id: this.env.models['mail.message_seen_indicator'].computeId(99, 11),
            message: [['insert', {id: 99}]],
        }]],
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({ thread: [['link', thread]] });
    const lastSeenMessage = this.env.models['mail.message'].create({
        author: [['link', currentPartner]],
        body: "<p>You already saw me</p>",
        id: 100,
        threadCaches: [['link', thread.mainCache]],
    });
    const message = this.env.models['mail.message'].create({
        author: [['link', currentPartner]],
        body: "<p>Test</p>",
        id: 99,
        threadCaches: [['link', thread.mainCache]],
    });
    thread.update({
       partnerSeenInfos: [['create', [
            {
                lastSeenMessage: [['link', lastSeenMessage]],
                partner: [['link', currentPartner]],
            },
            {
                lastSeenMessage: [['link', lastSeenMessage]],
                partner: [['insert', {id: 100}]],
            },
        ]]],
    });
    await this.createMessageComponent(message, { threadViewerLocalId: threadViewer.localId });

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
    const currentPartner = this.env.models['mail.partner'].create({
        id: this.env.session.partner_id,
        display_name: "Demo User"
    });
    const thread = this.env.models['mail.thread'].create({
        id: 11,
        partnerSeenInfos: [['create', [
            {
                lastSeenMessage: [['insert', {id: 100}]],
                partner: [['link', currentPartner]],
            },
            {
                partner: [['insert', {id: 100}]],
                lastFetchedMessage: [['insert', {id: 100}]],
                lastSeenMessage: [['insert', {id: 99}]],
            },
        ]]],
        messageSeenIndicators: [['insert', {
            id: this.env.models['mail.message_seen_indicator'].computeId(100, 11),
            message: [['insert', {id: 100}]],
        }]],
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({ thread: [['link', thread]] });
    const message = this.env.models['mail.message'].create({
        author: [['link', currentPartner]],
        body: "<p>Test</p>",
        id: 100,
        threadCaches: [['link', thread.mainCache]],
    });
    await this.createMessageComponent(message, { threadViewerLocalId: threadViewer.localId });

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
        2,
        "message component should have two checks (V)"
    );
});

});
});
});

});
