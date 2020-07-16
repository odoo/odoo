odoo.define('mail/static/src/components/thread_viewer/thread_viewer_tests.js', function (require) {
'use strict';

const components = {
    ThreadViewer: require('mail/static/src/components/thread_viewer/thread_viewer.js'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    dragenterFiles,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_viewer', {}, function () {
QUnit.module('thread_viewer_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        /**
         * @param {mail.thread_viewer} threadViewer
         * @param {Object} [otherProps={}]
         * @param {Object} [param2={}]
         * @param {boolean} [param2.isFixedSize=false]
         */
        this.createThreadViewerComponent = async (threadViewer, otherProps = {}, { isFixedSize = false } = {}) => {
            const ThreadViewerComponent = components.ThreadViewer;
            ThreadViewerComponent.env = this.env;
            this.component = new ThreadViewerComponent(
                null,
                Object.assign({ threadViewerLocalId: threadViewer.localId }, otherProps)
            );
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
            await afterNextRender(() => this.component.mount(target));
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
        delete components.ThreadViewer.env;
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
    const threadViewer = this.env.models['mail.thread_viewer'].create({ thread: [['link', thread]] });
    await this.createThreadViewerComponent(threadViewer, { hasComposer: true });
    await afterNextRender(() =>
        dragenterFiles(document.querySelector('.o_ThreadViewer'))
    );
    assert.ok(
        document.querySelector('.o_Composer_dropZone'),
        "should have dropzone when dragging file over the thread"
    );
});

QUnit.test('message list desc order', async function (assert) {
    assert.expect(8);

    let lastId = 10000;
    let amountOfCalls = 0;
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                amountOfCalls ++;
                assert.step(`message_fetch_${amountOfCalls}`);
                // Just return 30 different messages
                const messagesData = [...Array(30).keys()].reduce(function (acc, i) {
                    acc.push({
                        author_id: [i + 1, `Author #${i}`],
                        body: `<p>The message</p>`,
                        channel_ids: [20],
                        date: "2019-04-20 10:00:00",
                        id: lastId - i,
                        message_type: 'comment',
                        model: 'mail.channel',
                        record_name: 'General',
                        res_id: 20,
                    });
                    return acc;
                }, []);
                lastId -= 30;
                return messagesData;
            }
            return this._super(...arguments);
        },
    });
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
    const threadViewer = this.env.models['mail.thread_viewer'].create({ thread: [['link', thread]] });
    await this.createThreadViewerComponent(threadViewer, { order: 'desc' }, { isFixedSize: true });
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
        document.querySelector(`.o_ThreadViewer_messageList`).scrollTop =
            document.querySelector(`.o_ThreadViewer_messageList`).scrollHeight;
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        60,
        "should have 60 messages after scrolled to bottom"
    );

    await afterNextRender(() => {
        document.querySelector(`.o_ThreadViewer_messageList`).scrollTop = 0;
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        60,
        "scrolling to top should not trigger any message fetching"
    );
    assert.verifySteps(['message_fetch_1', 'message_fetch_2']);
});

QUnit.test('message list asc order', async function (assert) {
    assert.expect(8);

    let lastId = 10000;
    let amountOfCalls = 0;
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                amountOfCalls ++;
                assert.step(`message_fetch_${amountOfCalls}`);
                // Just return 30 different messages
                const messagesData = [...Array(30).keys()].reduce(function (acc, i) {
                    acc.push({
                        author_id: [i + 1, `Author #${i}`],
                        body: `<p>The message</p>`,
                        channel_ids: [20],
                        date: "2019-04-20 10:00:00",
                        id: lastId - i,
                        message_type: 'comment',
                        model: 'mail.channel',
                        record_name: 'General',
                        res_id: 20,
                    });
                    return acc;
                }, []);
                lastId -= 30;
                return messagesData;
            }
            return this._super(...arguments);
        },
    });
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
    const threadViewer = this.env.models['mail.thread_viewer'].create({ thread: [['link', thread]] });
    await this.createThreadViewerComponent(threadViewer, { order: 'asc' }, { isFixedSize: true });
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
        document.querySelector(`.o_ThreadViewer_messageList`).scrollTop = 0;
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        60,
        "should have 60 messages after scrolled to top"
    );

    // scroll to bottom
    await afterNextRender(() => {
        document.querySelector(`.o_ThreadViewer_messageList`).scrollTop =
            document.querySelector(`.o_ThreadViewer_messageList`).scrollHeight;
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        60,
        "scrolling to bottom should not trigger any message fetching"
    );
    assert.verifySteps(['message_fetch_1', 'message_fetch_2']);
});

QUnit.test('mark channel as fetched when a new message is loaded and as seen when focusing composer', async function (assert) {
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
        // FIXME should not be needed, see task-2277537
        composer: [['create']], // avoid initial focus
        id: 100,
        isServerPinned: true, // just to avoid joinChannel to be called
        members: [['insert', [
            {
                email: "john@example.com",
                id: this.env.session.partner_id,
                name: "John",
            },
            {
                email: "fred@example.com",
                id: 10,
                name: "Fred",
            },
        ]]],
        message_unread_counter: 1, // seen would not be called if not > 0
        model: 'mail.channel',
    });

    const threadViewer = this.env.models['mail.thread_viewer'].create({ thread: [['link', thread]] });
    await this.createThreadViewerComponent(threadViewer, { hasComposer: true });
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

    await afterNextRender(() => thread.composer.focus());
    assert.verifySteps(
        ['rpc:channel_seen'],
        "Channel should have been marked as seen after threadViewer got the focus"
    );
});

QUnit.test('mark channel as fetched and seen when a new message is loaded if composer is focused', async function (assert) {
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
                id: this.env.session.partner_id,
                name: "John",
            },
            {
                email: "fred@example.com",
                id: 10,
                name: "Fred",
            },
        ]]],
        message_unread_counter: 1, // seen would not be called if not > 0
        model: 'mail.channel',
    });

    const threadViewer = this.env.models['mail.thread_viewer'].create({ thread: [['link', thread]] });
    await this.createThreadViewerComponent(threadViewer, { hasComposer: true });
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

    this.data['mail.message'].records = [{
        author_id: [7, "Demo"],
        body: "<p>Test</p>",
        channel_ids: [100],
        date: "2019-04-20 11:00:00",
        id: 100,
        is_discussion: false,
        is_notification: false,
        message_type: 'comment',
        model: 'mail.channel',
        res_id: 20,
        subject: "Salutations, voyageur",
    }];
    await this.start();
    const thread = this.env.models['mail.thread'].create({
        channel_type: 'channel',
        id: 100,
        mass_mailing: true,
        model: 'mail.channel',
        name: "General",
        public: 'public',
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({ thread: [['link', thread]] });
    await this.createThreadViewerComponent(threadViewer);

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
    )
});

});
});
});

});
