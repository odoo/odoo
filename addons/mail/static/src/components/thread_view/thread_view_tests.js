odoo.define('mail/static/src/components/thread_view/thread_view_tests.js', function (require) {
'use strict';

const components = {
    ThreadView: require('mail/static/src/components/thread_view/thread_view.js'),
};
const {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    dragenterFiles,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_view', {}, function () {
QUnit.module('thread_view_tests.js', {
    beforeEach() {
        beforeEach(this);

        /**
         * @param {mail.thread_view} threadView
         * @param {Object} [otherProps={}]
         * @param {Object} [param2={}]
         * @param {boolean} [param2.isFixedSize=false]
         */
        this.createThreadViewComponent = async (threadView, otherProps = {}, { isFixedSize = false } = {}) => {
            let target;
            if (isFixedSize) {
                // needed to allow scrolling in some tests
                const div = document.createElement('div');
                Object.assign(div.style, {
                    display: 'flex',
                    'flex-flow': 'column',
                    height: '300px',
                });
                this.widget.el.append(div);
                target = div;
            } else {
                target = this.widget.el;
            }
            const props = Object.assign({ threadViewLocalId: threadView.localId }, otherProps);
            await createRootComponent(this, components.ThreadView, { props, target });
        };

        this.start = async params => {
            const { afterEvent, env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.afterEvent = afterEvent;
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('dragover files on thread with composer', async function (assert) {
    assert.expect(1);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        channel_type: 'channel',
        id: 100,
        members: [['insert', [
            {
                email: "john@example.com",
                id: 9,
                name: "John",
            },
            {
                email: "fred@example.com",
                id: 10,
                name: "Fred",
            },
        ]]],
        model: 'mail.channel',
        name: "General",
        public: 'public',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });
    await afterNextRender(() =>
        dragenterFiles(document.querySelector('.o_ThreadView'))
    );
    assert.ok(
        document.querySelector('.o_Composer_dropZone'),
        "should have dropzone when dragging file over the thread"
    );
});

QUnit.test('message list desc order', async function (assert) {
    assert.expect(5);

    for (let i = 0; i <= 60; i++) {
        this.data['mail.message'].records.push({
            channel_ids: [100],
            model: 'mail.channel',
            res_id: 100,
        });
    }
    await this.start();
    const thread = this.env.models['mail.thread'].create({
        channel_type: 'channel',
        id: 100,
        members: [['insert', [
            {
                email: "john@example.com",
                id: 9,
                name: "John",
            },
            {
                email: "fred@example.com",
                id: 10,
                name: "Fred",
            },
        ]]],
        model: 'mail.channel',
        name: "General",
        public: 'public',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { order: 'desc' }, { isFixedSize: true });
    const messageItems = document.querySelectorAll(`.o_MessageList_item`);
    assert.notOk(
        messageItems[0].classList.contains("o_MessageList_loadMore"),
        "load more link should NOT be before messages"
    );
    assert.ok(
        messageItems[messageItems.length - 1].classList.contains("o_MessageList_loadMore"),
        "load more link should be after messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        30,
        "should have 30 messages at the beginning"
    );

    // scroll to bottom
    await afterNextRender(() => {
        document.querySelector(`.o_ThreadView_messageList`).scrollTop =
            document.querySelector(`.o_ThreadView_messageList`).scrollHeight;
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        60,
        "should have 60 messages after scrolled to bottom"
    );

    await afterNextRender(() => {
        document.querySelector(`.o_ThreadView_messageList`).scrollTop = 0;
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        60,
        "scrolling to top should not trigger any message fetching"
    );
});

QUnit.test('message list asc order', async function (assert) {
    assert.expect(5);

    for (let i = 0; i <= 60; i++) {
        this.data['mail.message'].records.push({
            channel_ids: [100],
            model: 'mail.channel',
            res_id: 100,
        });
    }
    await this.start();
    const thread = this.env.models['mail.thread'].create({
        channel_type: 'channel',
        id: 100,
        members: [['insert', [
            {
                email: "john@example.com",
                id: 9,
                name: "John",
            },
            {
                email: "fred@example.com",
                id: 10,
                name: "Fred",
            },
        ]]],
        model: 'mail.channel',
        name: "General",
        public: 'public',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { order: 'asc' }, { isFixedSize: true });
    const messageItems = document.querySelectorAll(`.o_MessageList_item`);
    assert.notOk(
        messageItems[messageItems.length - 1].classList.contains("o_MessageList_loadMore"),
        "load more link should be before messages"
    );
    assert.ok(
        messageItems[0].classList.contains("o_MessageList_loadMore"),
        "load more link should NOT be after messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        30,
        "should have 30 messages at the beginning"
    );

    // scroll to top
    await afterNextRender(() => {
        document.querySelector(`.o_ThreadView_messageList`).scrollTop = 0;
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        60,
        "should have 60 messages after scrolled to top"
    );

    // scroll to bottom
    await afterNextRender(() => {
        document.querySelector(`.o_ThreadView_messageList`).scrollTop =
            document.querySelector(`.o_ThreadView_messageList`).scrollHeight;
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        60,
        "scrolling to bottom should not trigger any message fetching"
    );
});

QUnit.test('mark channel as fetched when a new message is loaded and as seen when focusing composer [REQUIRE FOCUS]', async function (assert) {
    assert.expect(8);

    await this.start({
        mockRPC(route, args) {
            if (args.method === 'channel_fetched') {
                assert.strictEqual(
                    args.args[0][0],
                    100,
                    'channel_fetched is called on the right channel id'
                );
                assert.strictEqual(
                    args.model,
                    'mail.channel',
                    'channel_fetched is called on the right channel model'
                );
                assert.step('rpc:channel_fetch');
            } else if (args.method === 'channel_seen') {
                assert.strictEqual(
                    args.args[0][0],
                    100,
                    'channel_seen is called on the right channel id'
                );
                assert.strictEqual(
                    args.model,
                    'mail.channel',
                    'channel_seeb is called on the right channel model'
                );
                assert.step('rpc:channel_seen');
            }
            return this._super(...arguments);
        }
    });
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        isServerPinned: true, // just to avoid joinChannel to be called
        members: [['insert', [
            {
                email: "john@example.com",
                id: this.env.messaging.currentPartner.id,
                name: "John",
            },
            {
                email: "fred@example.com",
                id: 10,
                name: "Fred",
            },
        ]]],
        model: 'mail.channel',
        serverMessageUnreadCounter: 1, // seen would not be called if not > 0
    });

    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });
    const notifications = [
        [['myDB', 'mail.channel', 100], {
            channelId: 100,
            id: 1,
            body: "<p>fdsfsd</p>",
            author_id: [10, "Fred"],
            model: "mail.channel",
            channel_ids: [100],
        }]
    ];

    await afterNextRender(() =>
        this.widget.call('bus_service', 'trigger', 'notification', notifications)
    );
    assert.verifySteps(
        ['rpc:channel_fetch'],
        "Channel should have been fetched but not seen yet"
    );

    await afterNextRender(() => document.querySelector('.o_ComposerTextInput_textarea').focus());
    assert.verifySteps(
        ['rpc:channel_seen'],
        "Channel should have been marked as seen after threadView got the focus"
    );
});

QUnit.test('mark channel as fetched and seen when a new message is loaded if composer is focused [REQUIRE FOCUS]', async function (assert) {
    assert.expect(4);

    await this.start({
        mockRPC(route, args) {
            if (args.method === 'channel_fetched' && args.args[0] === 100) {
                throw new Error("'channel_fetched' RPC must not be called for created channel as message is directly seen");
            } else if (args.method === 'channel_seen') {
                assert.strictEqual(
                    args.args[0][0],
                    100,
                    'channel_seen is called on the right channel id'
                );
                assert.strictEqual(
                    args.model,
                    'mail.channel',
                    'channel_seen is called on the right channel model'
                );
                assert.step('rpc:channel_seen');
            }
            return this._super(...arguments);
        }
    });
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        isServerPinned: true, // just to avoid joinChannel to be called
        members: [['insert', [
            {
                email: "john@example.com",
                id: this.env.messaging.currentPartner.id,
                name: "John",
            },
            {
                email: "fred@example.com",
                id: 10,
                name: "Fred",
            },
        ]]],
        model: 'mail.channel',
        serverMessageUnreadCounter: 1, // seen would not be called if not > 0
    });

    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });
    document.querySelector('.o_ComposerTextInput_textarea').focus();
    const notifications = [
        [['myDB', 'mail.channel', 100], {
            channelId: 100,
            id: 1,
            body: "<p>fdsfsd</p>",
            author_id: [10, "Fred"],
            model: "mail.channel",
            channel_ids: [100],
        }]
    ];
    await afterNextRender(() =>
        this.widget.call('bus_service', 'trigger', 'notification', notifications)
    );
    assert.verifySteps(
        ['rpc:channel_seen'],
        "Channel should have been mark as seen directly"
    );
});

QUnit.test('show message subject if thread is mailing channel', async function (assert) {
    assert.expect(3);

    this.data['mail.message'].records.push({
        channel_ids: [100],
        model: 'mail.channel',
        res_id: 100,
        subject: "Salutations, voyageur",
    });
    await this.start();
    const thread = this.env.models['mail.thread'].create({
        channel_type: 'channel',
        id: 100,
        mass_mailing: true,
        model: 'mail.channel',
        name: "General",
        public: 'public',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView);

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

QUnit.test('new messages separator on posting message', async function (assert) {
    assert.expect(4);

    this.data['mail.channel'].records = [{
        channel_type: 'channel',
        id: 20,
        is_pinned: true,
        message_unread_counter: 0,
        name: "General",
    }];
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel'
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });

    assert.containsNone(
        document.body,
        '.o_MessageList_message',
        "should have no messages"
    );
    assert.containsNone(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "should not display 'new messages' separator"
    );

    document.querySelector('.o_ComposerTextInput_textarea').focus();
    await afterNextRender(() => document.execCommand('insertText', false, "hey !"));
    await afterNextRender(() =>
        document.querySelector('.o_Composer_buttonSend').click()
    );
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should have the message current partner just posted"
    );
    assert.containsNone(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "still no separator shown when current partner posted a message"
    );
});

QUnit.test('new messages separator on receiving new message', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records.push({
        id:11,
        name: "Foreigner partner",
    });
    this.data['res.users'].records.push({
        id: 42,
        name: "Foreigner user",
        partner_id: 11,
    });
    this.data['mail.channel'].records.push({
        channel_type: 'channel',
        id: 20,
        is_pinned: true,
        message_unread_counter: 0,
        name: "General",
        seen_message_id: 1,
        uuid: 'randomuuid',
    });
    this.data['mail.message'].records.push({
        body: "blah",
        channel_ids: [20],
        id: 1,
    });
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel'
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });

    assert.containsOnce(
        document.body,
        '.o_MessageList_message',
        "should have an initial message"
    );
    assert.containsNone(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "should not display 'new messages' separator"
    );

    document.querySelector('.o_ComposerTextInput_textarea').blur();
    // simulate receiving a message
    await afterNextRender(async () => this.env.services.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: 42,
            },
            uuid: thread.uuid,
            message_content: "hu",
        },
    }));
    assert.containsN(
        document.body,
        '.o_Message',
        2,
        "should now have 2 messages after receiving a new message"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "'new messages' separator should be shown"
    );

    assert.containsOnce(
        document.body,
        `.o_MessageList_separatorNewMessages ~ .o_Message[data-message-local-id="${
            this.env.models['mail.message'].findFromIdentifyingData({id: 2}).localId
        }"]`,
        "'new messages' separator should be shown above new message received"
    );

    await afterNextRender(() => document.querySelector('.o_ComposerTextInput_textarea').focus());
    assert.containsNone(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "'new messages' separator should no longer be shown as last message has been seen"
    );
});

QUnit.test('new messages separator on posting message', async function (assert) {
    assert.expect(4);

    this.data['mail.channel'].records = [{
        channel_type: 'channel',
        id: 20,
        is_pinned: true,
        message_unread_counter: 0,
        name: "General",
    }];
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel'
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });

    assert.containsNone(
        document.body,
        '.o_MessageList_message',
        "should have no messages"
    );
    assert.containsNone(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "should not display 'new messages' separator"
    );

    document.querySelector('.o_ComposerTextInput_textarea').focus();
    await afterNextRender(() => document.execCommand('insertText', false, "hey !"));
    await afterNextRender(() =>
        document.querySelector('.o_Composer_buttonSend').click()
    );
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should have the message current partner just posted"
    );
    assert.containsNone(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "still no separator shown when current partner posted a message"
    );
});

QUnit.test('new messages separator on receiving new message', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records.push({
        id:11,
        name: "Foreigner partner",
    });
    this.data['res.users'].records.push({
        id: 42,
        name: "Foreigner user",
        partner_id: 11,
    });
    this.data['mail.channel'].records.push({
        channel_type: 'channel',
        id: 20,
        is_pinned: true,
        message_unread_counter: 0,
        name: "General",
        seen_message_id: 1,
        uuid: 'randomuuid',
    });
    this.data['mail.message'].records.push({
        body: "blah",
        channel_ids: [20],
        id: 1,
    });
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel'
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });

    assert.containsOnce(
        document.body,
        '.o_MessageList_message',
        "should have an initial message"
    );
    assert.containsNone(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "should not display 'new messages' separator"
    );

    document.querySelector('.o_ComposerTextInput_textarea').blur();
    // simulate receiving a message
    await afterNextRender(async () => this.env.services.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: 42,
            },
            uuid: thread.uuid,
            message_content: "hu",
        },
    }));
    assert.containsN(
        document.body,
        '.o_Message',
        2,
        "should now have 2 messages after receiving a new message"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "'new messages' separator should be shown"
    );

    assert.containsOnce(
        document.body,
        `.o_MessageList_separatorNewMessages ~ .o_Message[data-message-local-id="${
            this.env.models['mail.message'].findFromIdentifyingData({id: 2}).localId
        }"]`,
        "'new messages' separator should be shown above new message received"
    );

    await afterNextRender(() => document.querySelector('.o_ComposerTextInput_textarea').focus());
    assert.containsNone(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "'new messages' separator should no longer be shown as last message has been seen"
    );
});

QUnit.test('basic rendering of canceled notification', async function (assert) {
    assert.expect(8);

    this.data['mail.channel'].records.push({ id: 11 });
    this.data['res.partner'].records.push({ id: 12, name: "Someone" });
    this.data['mail.message'].records.push({
        channel_ids: [11],
        id: 10,
        message_type: 'email',
        model: 'mail.channel',
        notification_ids: [11],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        failure_type: 'SMTP',
        id: 11,
        mail_message_id: 10,
        notification_status: 'canceled',
        notification_type: 'email',
        res_partner_id: 12,
    });
    await this.start();
    const threadViewer = await this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['insert', {
            id: 11,
            model: 'mail.channel',
        }]],
    });
    await this.afterEvent({
        eventName: 'o-component-message-list-thread-cache-changed',
        func: () => {
            this.createThreadViewComponent(threadViewer.threadView);
        },
        message: "thread become loaded with messages",
        predicate: ({ threadViewer }) => {
            return threadViewer.thread.model === 'mail.channel' && threadViewer.thread.id === 11;
        },
    });

    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconClickable',
        "should display the notification icon container on the message"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon on the message"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-envelope-o',
        "notification icon shown on the message should represent email"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconClickable').click();
    });
    assert.containsOnce(
        document.body,
        '.o_NotificationPopover',
        "notification popover should be opened after notification has been clicked"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationPopover_notificationIcon',
        "an icon should be shown in notification popover"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationPopover_notificationIcon.fa.fa-trash-o',
        "the icon shown in notification popover should be the canceled icon"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationPopover_notificationPartnerName',
        "partner name should be shown in notification popover"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationPopover_notificationPartnerName').textContent.trim(),
        "Someone",
        "partner name shown in notification popover should be the one concerned by the notification"
    );
});

});
});
});

});
