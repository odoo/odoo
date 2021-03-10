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
            body: "not empty",
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
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => this.createThreadViewComponent(threadViewer.threadView, { order: 'desc' }, { isFixedSize: true }),
        message: "should wait until channel 100 loaded initial messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 100
            );
        },
    });
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
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            const messageList = document.querySelector('.o_ThreadView_messageList');
            messageList.scrollTop = messageList.scrollHeight - messageList.clientHeight;
        },
        message: "should wait until channel 100 loaded more messages after scrolling to bottom",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'more-messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 100
            );
        },
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
            body: "not empty",
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
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => this.createThreadViewComponent(threadViewer.threadView, { order: 'asc' }, { isFixedSize: true }),
        message: "should wait until channel 100 loaded initial messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 100
            );
        },
    });
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
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => document.querySelector(`.o_ThreadView_messageList`).scrollTop = 0,
        message: "should wait until channel 100 loaded more messages after scrolling to top",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'more-messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 100
            );
        },
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

    this.data['res.partner'].records.push({
        email: "fred@example.com",
        id: 10,
        name: "Fred",
    });
    this.data['res.users'].records.push({
        id: 10,
        partner_id: 10,
    });
    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 100,
        is_pinned: true,
        members: [this.data.currentPartnerId, 10],
    });
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
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 100,
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });
    await afterNextRender(async () => this.env.services.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: 10,
            },
            message_content: "new message",
            uuid: thread.uuid,
        },
    }));
    assert.verifySteps(
        ['rpc:channel_fetch'],
        "Channel should have been fetched but not seen yet"
    );

    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-last-seen-by-current-partner-message-id-changed',
        func: () => document.querySelector('.o_ComposerTextInput_textarea').focus(),
        message: "should wait until last seen by current partner message id changed after focusing the thread",
        predicate: ({ thread }) => {
            return (
                thread.id === 100 &&
                thread.model === 'mail.channel'
            );
        },
    }));
    assert.verifySteps(
        ['rpc:channel_seen'],
        "Channel should have been marked as seen after threadView got the focus"
    );
});

QUnit.test('mark channel as fetched and seen when a new message is loaded if composer is focused [REQUIRE FOCUS]', async function (assert) {
    assert.expect(4);

    this.data['res.partner'].records.push({
        id: 10,
    });
    this.data['res.users'].records.push({
        id: 10,
        partner_id: 10,
    });
    this.data['mail.channel'].records.push({
        id: 100,
    });
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
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 100,
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });
    document.querySelector('.o_ComposerTextInput_textarea').focus();
    // simulate receiving a message
    await this.afterEvent({
        eventName: 'o-thread-last-seen-by-current-partner-message-id-changed',
        func: () => this.env.services.rpc({
            route: '/mail/chat_post',
            params: {
                context: {
                    mockedUserId: 10,
                },
                message_content: "<p>fdsfsd</p>",
                uuid: thread.uuid,
            },
        }),
        message: "should wait until last seen by current partner message id changed after receiving a message while thread is focused",
        predicate: ({ thread }) => {
            return (
                thread.id === 100 &&
                thread.model === 'mail.channel'
            );
        },
    });
    assert.verifySteps(
        ['rpc:channel_seen'],
        "Channel should have been mark as seen directly"
    );
});

QUnit.test('show message subject if thread is mailing channel', async function (assert) {
    assert.expect(3);

    this.data['mail.message'].records.push({
        body: "not empty",
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

QUnit.test('[technical] new messages separator on posting message', async function (assert) {
    // technical as we need to remove focus from text input to avoid `channel_seen` call
    assert.expect(4);

    this.data['mail.channel'].records = [{
        channel_type: 'channel',
        id: 20,
        is_pinned: true,
        message_unread_counter: 0,
        seen_message_id: 10,
        name: "General",
    }];
    this.data['mail.message'].records.push({
        body: "first message",
        channel_ids: [20],
        id: 10,
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
        '.o_Message',
        "should display one message in thread initially"
    );
    assert.containsNone(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "should not display 'new messages' separator"
    );

    document.querySelector('.o_ComposerTextInput_textarea').focus();
    await afterNextRender(() => document.execCommand('insertText', false, "hey !"));
    await afterNextRender(() => {
        // need to remove focus from text area to avoid channel_seen
        document.querySelector('.o_Composer_buttonSend').focus();
        document.querySelector('.o_Composer_buttonSend').click();

    });
    assert.containsN(
        document.body,
        '.o_Message',
        2,
        "should display 2 messages (initial & newly posted), after posting a message"
    );
    assert.containsNone(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "still no separator shown when current partner posted a message"
    );
});

QUnit.test('new messages separator on receiving new message [REQUIRE FOCUS]', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records.push({
        id: 11,
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
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => this.env.services.rpc({
            route: '/mail/chat_post',
            params: {
                context: {
                    mockedUserId: 42,
                },
                message_content: "hu",
                uuid: thread.uuid,
            },
        }),
        message: "should wait until new message is received",
        predicate: ({ hint, threadViewer }) => {
            return (
                threadViewer.thread.id === 20 &&
                threadViewer.thread.model === 'mail.channel' &&
                hint.type === 'message-received'
            );
        },
    });
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
            this.env.models['mail.message'].findFromIdentifyingData({ id: 2 }).localId
        }"]`,
        "'new messages' separator should be shown above new message received"
    );

    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-last-seen-by-current-partner-message-id-changed',
        func: () => document.querySelector('.o_ComposerTextInput_textarea').focus(),
        message: "should wait until last seen by current partner message id changed after focusing the thread",
        predicate: ({ thread }) => {
            return (
                thread.id === 20 &&
                thread.model === 'mail.channel'
            );
        },
    }));
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

QUnit.test('basic rendering of canceled notification', async function (assert) {
    assert.expect(8);

    this.data['mail.channel'].records.push({ id: 11 });
    this.data['res.partner'].records.push({ id: 12, name: "Someone" });
    this.data['mail.message'].records.push({
        body: "not empty",
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
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            this.createThreadViewComponent(threadViewer.threadView);
        },
        message: "thread become loaded with messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 11
            );
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

QUnit.test('should scroll to bottom on receiving new message if the list is initially scrolled to bottom (asc order)', async function (assert) {
    assert.expect(2);

    // Needed partner & user to allow simulation of message reception
    this.data['res.partner'].records.push({
        id: 11,
        name: "Foreigner partner",
    });
    this.data['res.users'].records.push({
        id: 42,
        name: "Foreigner user",
        partner_id: 11,
    });
    this.data['mail.channel'].records.push({ id: 20 });
    for (let i = 0; i <= 10; i++) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [20],
        });
    }
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel'
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => this.createThreadViewComponent(
            threadViewer.threadView,
            { order: 'asc' },
            { isFixedSize: true },
        ),
        message: "should wait until channel 20 scrolled initially",
        predicate: data => threadViewer === data.threadViewer,
    });
    const initialMessageList = document.querySelector('.o_ThreadView_messageList');
    assert.strictEqual(
        initialMessageList.scrollTop,
        initialMessageList.scrollHeight - initialMessageList.clientHeight,
        "should have scrolled to bottom of channel 20 initially"
    );

    // simulate receiving a message
    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () =>
            this.env.services.rpc({
                route: '/mail/chat_post',
                params: {
                    context: {
                        mockedUserId: 42,
                    },
                    message_content: "hello",
                    uuid: thread.uuid,
                },
            }),
        message: "should wait until channel 20 scrolled after receiving a message",
        predicate: data => threadViewer === data.threadViewer,
    });
    const messageList = document.querySelector('.o_ThreadView_messageList');
    assert.strictEqual(
        messageList.scrollTop,
        messageList.scrollHeight - messageList.clientHeight,
        "should scroll to bottom on receiving new message because the list is initially scrolled to bottom"
    );
});

QUnit.test('should not scroll on receiving new message if the list is initially scrolled anywhere else than bottom (asc order)', async function (assert) {
    assert.expect(3);

    // Needed partner & user to allow simulation of message reception
    this.data['res.partner'].records.push({
        id: 11,
        name: "Foreigner partner",
    });
    this.data['res.users'].records.push({
        id: 42,
        name: "Foreigner user",
        partner_id: 11,
    });
    this.data['mail.channel'].records.push({ id: 20 });
    for (let i = 0; i <= 10; i++) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [20],
        });
    }
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel'
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => this.createThreadViewComponent(
            threadViewer.threadView,
            { order: 'asc' },
            { isFixedSize: true },
        ),
        message: "should wait until channel 20 scrolled initially",
        predicate: data => threadViewer === data.threadViewer,
    });
    const initialMessageList = document.querySelector('.o_ThreadView_messageList');
    assert.strictEqual(
        initialMessageList.scrollTop,
        initialMessageList.scrollHeight - initialMessageList.clientHeight,
        "should have scrolled to bottom of channel 20 initially"
    );

    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => initialMessageList.scrollTop = 0,
        message: "should wait until channel 20 processed manual scroll",
        predicate: data => threadViewer === data.threadViewer,
    });
    assert.strictEqual(
        initialMessageList.scrollTop,
        0,
        "should have scrolled to the top of channel 20 manually"
    );

    // simulate receiving a message
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () =>
            this.env.services.rpc({
                route: '/mail/chat_post',
                params: {
                    context: {
                        mockedUserId: 42,
                    },
                    message_content: "hello",
                    uuid: thread.uuid,
                },
            }),
        message: "should wait until channel 20 processed new message hint",
        predicate: data => threadViewer === data.threadViewer && data.hint.type === 'message-received',
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadView_messageList').scrollTop,
        0,
        "should not scroll on receiving new message because the list is initially scrolled anywhere else than bottom"
    );
});

QUnit.test("delete all attachments of message without content should no longer display the message", async function (assert) {
    assert.expect(2);

    this.data['ir.attachment'].records.push({
        id: 143,
        mimetype: 'text/plain',
        name: "Blah.txt",
    });
    this.data['mail.channel'].records.push({ id: 11 });
    this.data['mail.message'].records.push(
        {
            attachment_ids: [143],
            channel_ids: [11],
            id: 101,
        }
    );
    await this.start();
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['insert', { id: 11, model: 'mail.channel' }]],
    });
    // wait for messages of the thread to be loaded
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            this.createThreadViewComponent(threadViewer.threadView);
        },
        message: "thread become loaded with messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 11
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "there should be 1 message displayed initially"
    );

    await afterNextRender(() => {
        document.querySelector(`.o_Attachment[data-attachment-local-id="${
            this.env.models['mail.attachment'].findFromIdentifyingData({ id: 143 }).localId
        }"] .o_Attachment_asideItemUnlink`).click();
    });
    await afterNextRender(() =>
        document.querySelector('.o_AttachmentDeleteConfirmDialog_confirmButton').click()
    );
    assert.containsNone(
        document.body,
        '.o_Message',
        "message should no longer be displayed after removing all its attachments (empty content)"
    );
});

QUnit.test('delete all attachments of a message with some text content should still keep it displayed', async function (assert) {
    assert.expect(2);

    this.data['ir.attachment'].records.push({
        id: 143,
        mimetype: 'text/plain',
        name: "Blah.txt",
    });
    this.data['mail.channel'].records.push({ id: 11 });
    this.data['mail.message'].records.push(
        {
            attachment_ids: [143],
            body: "Some content",
            channel_ids: [11],
            id: 101,
        },
    );
    await this.start();
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['insert', { id: 11, model: 'mail.channel' }]],
    });
    // wait for messages of the thread to be loaded
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            this.createThreadViewComponent(threadViewer.threadView);
        },
        message: "thread become loaded with messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 11
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "there should be 1 message displayed initially"
    );

    await afterNextRender(() => {
        document.querySelector(`.o_Attachment[data-attachment-local-id="${
            this.env.models['mail.attachment'].findFromIdentifyingData({ id: 143 }).localId
        }"] .o_Attachment_asideItemUnlink`).click();
    });
    await afterNextRender(() =>
        document.querySelector('.o_AttachmentDeleteConfirmDialog_confirmButton').click()
    );
    assert.containsOnce(
        document.body,
        '.o_Message',
        "message should still be displayed after removing its attachments (non-empty content)"
    );
});

QUnit.test('delete all attachments of a message with tracking fields should still keep it displayed', async function (assert) {
    assert.expect(2);

    this.data['ir.attachment'].records.push({
        id: 143,
        mimetype: 'text/plain',
        name: "Blah.txt",
    });
    this.data['mail.channel'].records.push({ id: 11 });
    this.data['mail.message'].records.push(
        {
            attachment_ids: [143],
            channel_ids: [11],
            id: 101,
            tracking_value_ids: [6]
        },
    );
    this.data['mail.tracking.value'].records.push({
        changed_field: "Name",
        field_type: "char",
        id: 6,
        new_value: "New name",
        old_value: "Old name",
    });
    await this.start();
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['insert', { id: 11, model: 'mail.channel' }]],
    });
    // wait for messages of the thread to be loaded
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            this.createThreadViewComponent(threadViewer.threadView);
        },
        message: "thread become loaded with messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 11
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "there should be 1 message displayed initially"
    );

    await afterNextRender(() => {
        document.querySelector(`.o_Attachment[data-attachment-local-id="${
            this.env.models['mail.attachment'].findFromIdentifyingData({ id: 143 }).localId
        }"] .o_Attachment_asideItemUnlink`).click();
    });
    await afterNextRender(() =>
        document.querySelector('.o_AttachmentDeleteConfirmDialog_confirmButton').click()
    );
    assert.containsOnce(
        document.body,
        '.o_Message',
        "message should still be displayed after removing its attachments (non-empty content)"
    );
});

QUnit.test('Post a message containing an email address followed by a mention on another line', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 11 });
    this.data['res.partner'].records.push({
        id: 25,
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 11,
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });
    document.querySelector('.o_ComposerTextInput_textarea').focus();
    await afterNextRender(() => document.execCommand('insertText', false, "email@odoo.com\n"));
    await afterNextRender(() => {
        ["@", "T", "e"].forEach((char)=>{
            document.execCommand('insertText', false, char);
            document.querySelector(`.o_ComposerTextInput_textarea`)
                .dispatchEvent(new window.KeyboardEvent('keydown'));
            document.querySelector(`.o_ComposerTextInput_textarea`)
                .dispatchEvent(new window.KeyboardEvent('keyup'));
        });
    });
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    await afterNextRender(() => {
        document.querySelector('.o_Composer_buttonSend').click();
    });
    assert.containsOnce(
        document.querySelector(`.o_Message_content`),
        `.o_mail_redirect[data-oe-id="25"][data-oe-model="res.partner"]:contains("@TestPartner")`,
        "Conversation should have a message that has been posted, which contains partner mention"
    );
});

QUnit.test(`Mention a partner with special character (e.g. apostrophe ')`, async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 11 });
    this.data['res.partner'].records.push({
        id: 1952,
        email: "usatyi@example.com",
        name: "Pynya's spokesman",
    });
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 11,
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });
    document.querySelector('.o_ComposerTextInput_textarea').focus();
    await afterNextRender(() => {
        ["@", "P", "y", "n"].forEach((char)=>{
            document.execCommand('insertText', false, char);
            document.querySelector(`.o_ComposerTextInput_textarea`)
                .dispatchEvent(new window.KeyboardEvent('keydown'));
            document.querySelector(`.o_ComposerTextInput_textarea`)
                .dispatchEvent(new window.KeyboardEvent('keyup'));
        });
    });
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    await afterNextRender(() => {
        document.querySelector('.o_Composer_buttonSend').click();
    });
    assert.containsOnce(
        document.querySelector(`.o_Message_content`),
        `.o_mail_redirect[data-oe-id="1952"][data-oe-model="res.partner"]:contains("@Pynya's spokesman")`,
        "Conversation should have a message that has been posted, which contains partner mention"
    );
});

QUnit.test('mention 2 different partners that have the same name', async function (assert) {
    assert.expect(3);

    this.data['mail.channel'].records.push({ id: 11 });
    this.data['res.partner'].records.push(
        {
            id: 25,
            email: "partner1@example.com",
            name: "TestPartner",
        }, {
            id: 26,
            email: "partner2@example.com",
            name: "TestPartner",
        },
    );
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 11,
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });
    document.querySelector('.o_ComposerTextInput_textarea').focus();
    await afterNextRender(() => {
        ["@", "T", "e"].forEach((char)=>{
            document.execCommand('insertText', false, char);
            document.querySelector(`.o_ComposerTextInput_textarea`)
                .dispatchEvent(new window.KeyboardEvent('keydown'));
            document.querySelector(`.o_ComposerTextInput_textarea`)
                .dispatchEvent(new window.KeyboardEvent('keyup'));
        });
    });
    await afterNextRender(() => document.querySelectorAll('.o_ComposerSuggestion')[0].click());
    await afterNextRender(() => {
        ["@", "T", "e"].forEach((char)=>{
            document.execCommand('insertText', false, char);
            document.querySelector(`.o_ComposerTextInput_textarea`)
                .dispatchEvent(new window.KeyboardEvent('keydown'));
            document.querySelector(`.o_ComposerTextInput_textarea`)
                .dispatchEvent(new window.KeyboardEvent('keyup'));
        });
    });
    await afterNextRender(() => document.querySelectorAll('.o_ComposerSuggestion')[1].click());
    await afterNextRender(() => document.querySelector('.o_Composer_buttonSend').click());
    assert.containsOnce(document.body, '.o_Message_content', 'should have one message after posting it');
    assert.containsOnce(
        document.querySelector(`.o_Message_content`),
        `.o_mail_redirect[data-oe-id="25"][data-oe-model="res.partner"]:contains("@TestPartner")`,
        "message should contain the first partner mention"
    );
    assert.containsOnce(
        document.querySelector(`.o_Message_content`),
        `.o_mail_redirect[data-oe-id="26"][data-oe-model="res.partner"]:contains("@TestPartner")`,
        "message should also contain the second partner mention"
    );
});

QUnit.test('mention a channel with space in the name', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({
        id: 7,
        name: "General good boy",
    });
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 7,
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });

    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "#");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    await afterNextRender(() => {
        document.querySelector('.o_Composer_buttonSend').click();
    });
    assert.containsOnce(
        document.querySelector('.o_Message_content'),
        '.o_channel_redirect',
        "message must contain a link to the mentioned channel"
    );
    assert.strictEqual(
        document.querySelector('.o_channel_redirect').textContent,
        '#General good boy',
        "link to the channel must contains # + the channel name"
    );
});

QUnit.test('mention a channel with "&" in the name', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({
        id: 7,
        name: "General & good",
    });
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 7,
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });

    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "#");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    await afterNextRender(() => {
        document.querySelector('.o_Composer_buttonSend').click();
    });
    assert.containsOnce(
        document.querySelector('.o_Message_content'),
        '.o_channel_redirect',
        "message should contain a link to the mentioned channel"
    );
    assert.strictEqual(
        document.querySelector('.o_channel_redirect').textContent,
        '#General & good',
        "link to the channel must contains # + the channel name"
    );
});

QUnit.test('mention a channel on a second line when the first line contains #', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({
        id: 7,
        name: "General good",
    });
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 7,
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });

    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "#blabla\n#");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    await afterNextRender(() => {
        document.querySelector('.o_ComposerSuggestion').click();
    });
    await afterNextRender(() => {
        document.querySelector('.o_Composer_buttonSend').click();
    });
    assert.containsOnce(
        document.querySelector('.o_Message_content'),
        '.o_channel_redirect',
        "message should contain a link to the mentioned channel"
    );
    assert.strictEqual(
        document.querySelector('.o_channel_redirect').textContent,
        '#General good',
        "link to the channel must contains # + the channel name"
    );
});

QUnit.test('mention a channel when replacing the space after the mention by another char', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({
        id: 7,
        name: "General good",
    });
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 7,
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });

    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "#");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    await afterNextRender(() => {
        document.querySelector('.o_ComposerSuggestion').click();
    });
    await afterNextRender(() => {
        const text = document.querySelector(`.o_ComposerTextInput_textarea`).value;
        document.querySelector(`.o_ComposerTextInput_textarea`).value = text.slice(0, -1);
        document.execCommand('insertText', false, ", test");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    await afterNextRender(() => {
        document.querySelector('.o_Composer_buttonSend').click();
    });
    assert.containsOnce(
        document.querySelector('.o_Message_content'),
        '.o_channel_redirect',
        "message should contain a link to the mentioned channel"
    );
    assert.strictEqual(
        document.querySelector('.o_channel_redirect').textContent,
        '#General good',
        "link to the channel must contains # + the channel name"
    );
});

QUnit.test('mention 2 different channels that have the same name', async function (assert) {
    assert.expect(3);

    this.data['mail.channel'].records.push(
        {
            id: 11,
            name: "my channel",
            public: 'public', // mentioning another channel is possible only from a public channel
        },
        {
            id: 12,
            name: "my channel",
        },
    );
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 11,
        model: 'mail.channel',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadViewComponent(threadViewer.threadView, { hasComposer: true });
    document.querySelector('.o_ComposerTextInput_textarea').focus();
    await afterNextRender(() => {
        ["#", "m", "y"].forEach((char)=>{
            document.execCommand('insertText', false, char);
            document.querySelector(`.o_ComposerTextInput_textarea`)
                .dispatchEvent(new window.KeyboardEvent('keydown'));
            document.querySelector(`.o_ComposerTextInput_textarea`)
                .dispatchEvent(new window.KeyboardEvent('keyup'));
        });
    });
    await afterNextRender(() => document.querySelectorAll('.o_ComposerSuggestion')[0].click());
    await afterNextRender(() => {
        ["#", "m", "y"].forEach((char)=>{
            document.execCommand('insertText', false, char);
            document.querySelector(`.o_ComposerTextInput_textarea`)
                .dispatchEvent(new window.KeyboardEvent('keydown'));
            document.querySelector(`.o_ComposerTextInput_textarea`)
                .dispatchEvent(new window.KeyboardEvent('keyup'));
        });
    });
    await afterNextRender(() => document.querySelectorAll('.o_ComposerSuggestion')[1].click());
    await afterNextRender(() => document.querySelector('.o_Composer_buttonSend').click());
    assert.containsOnce(document.body, '.o_Message_content', 'should have one message after posting it');
    assert.containsOnce(
        document.querySelector(`.o_Message_content`),
        `.o_channel_redirect[data-oe-id="11"][data-oe-model="mail.channel"]:contains("#my channel")`,
        "message should contain the first channel mention"
    );
    assert.containsOnce(
        document.querySelector(`.o_Message_content`),
        `.o_channel_redirect[data-oe-id="12"][data-oe-model="mail.channel"]:contains("#my channel")`,
        "message should also contain the second channel mention"
    );
});

QUnit.test('show empty placeholder when thread contains no message', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 11 });
    await this.start();
    const threadViewer = await this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['insert', {
            id: 11,
            model: 'mail.channel',
        }]],
    });
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            this.createThreadViewComponent(threadViewer.threadView);
        },
        message: "should wait until thread becomes loaded with messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 11
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_MessageList_empty',
        "message list empty placeholder should be shown as thread does not contain any messages"
    );
    assert.containsNone(
        document.body,
        '.o_Message',
        "no message should be shown as thread does not contain any"
    );
});

QUnit.test('show empty placeholder when thread contains only empty messages', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 11 });
    this.data['mail.message'].records.push(
        {
            channel_ids: [11],
            id: 101,
        },
    );
    await this.start();
    const threadViewer = await this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['insert', {
            id: 11,
            model: 'mail.channel',
        }]],
    });
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            this.createThreadViewComponent(threadViewer.threadView);
        },
        message: "thread become loaded with messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 11
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_MessageList_empty',
        "message list empty placeholder should be shown as thread contain only empty messages"
    );
    assert.containsNone(
        document.body,
        '.o_Message',
        "no message should be shown as thread contains only empty ones"
    );
});

QUnit.test('message with subtype should be displayed (and not considered as empty)', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 11 });
    this.data['mail.message.subtype'].records.push({
        description: "Task created",
        id: 10,
    });
    this.data['mail.message'].records.push(
        {
            channel_ids: [11],
            id: 101,
            subtype_id: 10,
        },
    );
    await this.start();
    const threadViewer = await this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['insert', {
            id: 11,
            model: 'mail.channel',
        }]],
    });
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            this.createThreadViewComponent(threadViewer.threadView);
        },
        message: "should wait until thread becomes loaded with messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 11
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display 1 message (message with subtype description 'task created')"
    );
    assert.strictEqual(
        document.body.querySelector('.o_Message_content').textContent,
        "Task created",
        "message should have 'Task created' (from its subtype description)"
    );
});

QUnit.test('[technical] message list with a full page of empty messages should show load more if there are other messages', async function (assert) {
    // Technical assumptions :
    // - message_fetch fetching exactly 30 messages,
    // - empty messages not being displayed
    // - auto-load more being triggered on scroll, not automatically when the 30 first messages are empty
    assert.expect(2);

    this.data['mail.channel'].records.push({
        id: 11,
    });
    for (let i = 0; i <= 30; i++) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [11],
        });
    }
    for (let i = 0; i <= 30; i++) {
        this.data['mail.message'].records.push({
            channel_ids: [11],
        });
    }
    await this.start();
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['insert', {
            id: 11,
            model: 'mail.channel',
        }]],
    });
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            this.createThreadViewComponent(threadViewer.threadView, { order: 'asc' }, { isFixedSize: true });
        },
        message: "should wait until thread becomes loaded with messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 11
            );
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "No message should be shown as all 30 first messages are empty"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageList_loadMore',
        "Load more button should be shown as there are more messages to show"
    );
});

QUnit.test('first unseen message should be directly preceded by the new message separator if there is a transient message just before it while composer is not focused [REQUIRE FOCUS]', async function (assert) {
    // The goal of removing the focus is to ensure the thread is not marked as seen automatically.
    // Indeed that would trigger channel_seen no matter what, which is already covered by other tests.
    // The goal of this test is to cover the conditions specific to transient messages,
    // and the conditions from focus would otherwise shadow them.
    assert.expect(3);

    this.data['mail.channel_command'].records.push({ name: 'who' });
    // Needed partner & user to allow simulation of message reception
    this.data['res.partner'].records.push({
        id: 11,
        name: "Foreigner partner",
    });
    this.data['res.users'].records.push({
        id: 42,
        name: "Foreigner user",
        partner_id: 11,
    });
    this.data['mail.channel'].records = [{
        channel_type: 'channel',
        id: 20,
        is_pinned: true,
        name: "General",
        uuid: 'channel20uuid',
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
    // send a command that leads to receiving a transient message
    document.querySelector('.o_ComposerTextInput_textarea').focus();
    await afterNextRender(() => document.execCommand('insertText', false, "/who"));
    await afterNextRender(() => {
        document.querySelector('.o_Composer_buttonSend').click();
    });

    // composer is focused by default, we remove that focus
    document.querySelector('.o_ComposerTextInput_textarea').blur();
    // simulate receiving a message
    await afterNextRender(() => this.env.services.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: 42,
            },
            message_content: "test",
            uuid: 'channel20uuid',
        },
    }));
    assert.containsN(
        document.body,
        '.o_Message',
        2,
        "should display 2 messages (the transient & the received message), after posting a command"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "separator should be shown as a message has been received"
    );
    assert.containsOnce(
        document.body,
        `.o_Message[data-message-local-id="${
            this.env.models['mail.message'].find(m => m.isTransient).localId
        }"] + .o_MessageList_separatorNewMessages`,
        "separator should be shown just after transient message"
    );
});

QUnit.test('composer should be focused automatically after clicking on the send button [REQUIRE FOCUS]', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({id: 20,});
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
    document.querySelector('.o_ComposerTextInput_textarea').focus();
    await afterNextRender(() => document.execCommand('insertText', false, "Dummy Message"));
    await afterNextRender(() => {
        document.querySelector('.o_Composer_buttonSend').click();
    });
    assert.hasClass(
        document.querySelector('.o_Composer'),
        'o-focused',
        "composer should be focused automatically after clicking on the send button"
    );
});

});
});
});

});
