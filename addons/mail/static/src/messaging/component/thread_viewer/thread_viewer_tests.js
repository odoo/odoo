odoo.define('mail.messaging.component.ThreadViewerTests', function (require) {
'use strict';

const components = {
    ThreadViewer: require('mail.messaging.component.ThreadViewer'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    dragenterFiles,
    nextAnimationFrame,
    pause,
    start: utilsStart,
} = require('mail.messaging.testUtils');

QUnit.module('mail', {}, function () {
QUnit.module('messaging', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('ThreadViewer', {
    beforeEach() {
        utilsBeforeEach(this);

        /**
         * @param {mail.messaging.entity.Thread} thread
         * @param {Object} [otherProps]
         */
        this.createThreadViewerComponent = async (threadViewer, otherProps, { isFixedSize = false } = {}) => {
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
            await this.component.mount(target);
            await afterNextRender();
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
    const thread = this.env.entities.Thread.create({
        channel_type: 'channel',
        id: 100,
        members: [
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
        ],
        name: "General",
        public: 'public',
    });
    const threadViewer = this.env.entities.ThreadViewer.create({ thread });
    await this.createThreadViewerComponent(threadViewer, { hasComposer: true });
    dragenterFiles(document.querySelector('.o_ThreadViewer'));
    await afterNextRender();
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
    const thread = this.env.entities.Thread.create({
        channel_type: 'channel',
        id: 100,
        members: [
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
        ],
        name: "General",
        public: 'public',
    });
    const threadViewer = this.env.entities.ThreadViewer.create({ thread });
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
    document.querySelector(`.o_ThreadViewer_messageList`).scrollTop =
        document.querySelector(`.o_ThreadViewer_messageList`).scrollHeight;
    // The following awaits should be afterNextRender but use multiple nextAnimationFrame
    // instead to know exactly how much time has to be waited for new messages
    // to appear (used below).
    await nextAnimationFrame();
    await nextAnimationFrame();
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        60,
        "should have 60 messages after scrolled to bottom"
    );

    document.querySelector(`.o_ThreadViewer_messageList`).scrollTop = 0;
    // This amount of time should be enough before assuming no messages will
    // appear (see above).
    await nextAnimationFrame();
    await nextAnimationFrame();
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
    const thread = this.env.entities.Thread.create({
        channel_type: 'channel',
        id: 100,
        members: [
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
        ],
        name: "General",
        public: 'public',
    });
    const threadViewer = this.env.entities.ThreadViewer.create({ thread });
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
    document.querySelector(`.o_ThreadViewer_messageList`).scrollTop = 0;
    // The following awaits should be afterNextRender but use multiple nextAnimationFrame
    // instead to know exactly how much time has to be waited for new messages
    // to appear (used below).
    await nextAnimationFrame();
    await nextAnimationFrame();
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        60,
        "should have 60 messages after scrolled to top"
    );

    // scroll to bottom
    document.querySelector(`.o_ThreadViewer_messageList`).scrollTop =
        document.querySelector(`.o_ThreadViewer_messageList`).scrollHeight;
    // This amount of time should be enough before assuming no messages will
    // appear (see above).
    await nextAnimationFrame();
    await nextAnimationFrame();
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        60,
        "scrolling to bottom should not trigger any message fetching"
    );
    assert.verifySteps(['message_fetch_1', 'message_fetch_2']);
});

});
});
});

});
