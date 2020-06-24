odoo.define('mail/static/src/components/thread_preview/thread_preview_tests.js', function (require) {
'use strict';

const components = {
    ThreadPreview: require('mail/static/src/components/thread_preview/thread_preview.js'),
};

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_preview', {}, function () {
QUnit.module('thread_preview_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createThreadPreviewComponent = async props => {
            const ThreadPreviewComponent = components.ThreadPreview;
            ThreadPreviewComponent.env = this.env;
            this.component = new ThreadPreviewComponent(null, props);
            delete ThreadPreviewComponent.env;
            await afterNextRender(() => this.component.mount(this.widget.el));
        };

        this.start = async params => {
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
            this.component = undefined;
        }
        if (this.widget) {
            this.widget.destroy();
            this.widget = undefined;
        }
        this.env = undefined;
    },
});

QUnit.test('mark as read', async function (assert) {
    assert.expect(4);

    await this.start({
        hasChatWindow: true,
        async mockRPC(route, args) {
            if (route.includes('channel_seen')) {
                assert.step('channel_seen');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].create({
        id: 11,
        message_unread_counter: 1,
        model: 'mail.channel',
    });
    await this.createThreadPreviewComponent({ threadLocalId: thread.localId });
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_markAsRead',
        "should have 1 mark as read button"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ThreadPreview_markAsRead').click()
    );
    assert.verifySteps(
        ['channel_seen'],
        "should have marked the thread as seen"
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
