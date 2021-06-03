odoo.define('mail/static/src/components/thread_preview/thread_preview_tests.js', function (require) {
'use strict';

const components = {
    ThreadPreview: require('mail/static/src/components/thread_preview/thread_preview.js'),
};

const {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_preview', {}, function () {
QUnit.module('thread_preview_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createThreadPreviewComponent = async props => {
            await createRootComponent(this, components.ThreadPreview, {
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

QUnit.test('Message from mailing channel should not make a notification', async function (assert) {
    assert.expect(3);

    await this.start({
        env: {
            session: {
                notification_type: "email"
            }
        },
        async mockRPC(route, args) {
            if (route.includes('channel_seen')) {
                assert.step('channel_seen');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].create({
        channel_type: 'channel',
        id: 100,
        mass_mailing: true,
        model: 'mail.channel',
        name: "General",
        public: 'public',
    });
    this.env.models['mail.message'].create({
        author: [['insert', { id: 1, display_name: "Admin" }]],
        body: "<p>Test 1</p>",
        id: 101,
        moderation_status: 'pending_moderation',
        originThread: [['link', thread]],
    });
    const threadViewer = this.env.models['mail.thread_viewer'].create({
        hasThreadView: true,
        thread: [['link', thread]],
    });
    await this.createThreadPreviewComponent({ threadLocalId: threadViewer.localId  });
    assert.containsNone(
        document.body,
        '.o_ThreadPreview_counter',
        "should not have notification counter"
    );
    assert.verifySteps(
        ['channel_seen'],
        "should have marked the thread as seen"
    );
});

QUnit.test('mark as read', async function (assert) {
    assert.expect(8);
    this.data['mail.channel'].records.push({
        id: 11,
        message_unread_counter: 1,
    });
    this.data['mail.message'].records.push({
        channel_ids: [11],
        id: 100,
        model: 'mail.channel',
        res_id: 11,
    });

    await this.start({
        hasChatWindow: true,
        async mockRPC(route, args) {
            if (route.includes('channel_seen')) {
                assert.step('channel_seen');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 11,
        model: 'mail.channel',
    });
    await this.createThreadPreviewComponent({ threadLocalId: thread.localId });
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_markAsRead',
        "should have the mark as read button"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_counter',
        "should have an unread counter"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ThreadPreview_markAsRead').click()
    );
    assert.verifySteps(
        ['channel_seen'],
        "should have marked the thread as seen"
    );
    assert.hasClass(
        document.querySelector('.o_ThreadPreview'),
        'o-muted',
        "should be muted once marked as read"
    );
    assert.containsNone(
        document.body,
        '.o_ThreadPreview_markAsRead',
        "should no longer have the mark as read button"
    );
    assert.containsNone(
        document.body,
        '.o_ThreadPreview_counter',
        "should no longer have an unread counter"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should not have opened the thread"
    );
});

});
});
});

});
