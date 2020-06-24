odoo.define('mail/static/src/components/thread_needaction_preview/thread_needaction_preview_tests.js', function (require) {
'use strict';

const components = {
    ThreadNeedactionPreview: require('mail/static/src/components/thread_needaction_preview/thread_needaction_preview.js'),
};

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_needaction_preview', {}, function () {
QUnit.module('thread_needaction_preview_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createThreadNeedactionPreviewComponent = async props => {
            const ThreadNeedactionPreviewComponent = components.ThreadNeedactionPreview;
            ThreadNeedactionPreviewComponent.env = this.env;
            this.component = new ThreadNeedactionPreviewComponent(null, props);
            delete ThreadNeedactionPreviewComponent.env;
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
            if (route.includes('set_message_done')) {
                assert.step('set_message_done');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].create({
        id: 11,
        model: 'mail.channel',
    });
    this.env.models['mail.message'].create({
        id: 21,
        isNeedaction: true,
        originThread: [['link', thread]],
    });
    await this.createThreadNeedactionPreviewComponent({
        threadLocalId: thread.localId,
    });
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_markAsRead',
        "should have 1 mark as read button"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ThreadNeedactionPreview_markAsRead').click()
    );
    assert.verifySteps(
        ['set_message_done'],
        "should have marked the message as read"
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
