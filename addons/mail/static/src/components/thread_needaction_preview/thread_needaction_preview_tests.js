odoo.define('mail/static/src/components/thread_needaction_preview/thread_needaction_preview_tests.js', function (require) {
'use strict';

const components = {
    ThreadNeedactionPreview: require('mail/static/src/components/thread_needaction_preview/thread_needaction_preview.js'),
};

const {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    start,
} = require('mail/static/src/utils/test_utils.js');

const Bus = require('web.Bus');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_needaction_preview', {}, function () {
QUnit.module('thread_needaction_preview_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createThreadNeedactionPreviewComponent = async props => {
            await createRootComponent(this, components.ThreadNeedactionPreview, {
                props,
                target: this.widget.el
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

QUnit.test('click on preview should mark as read and open the thread', async function (assert) {
    assert.expect(5);

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
        '.o_ThreadNeedactionPreview',
        "should have a preview initially"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should have no chat window initially"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ThreadNeedactionPreview').click()
    );
    assert.verifySteps(
        ['set_message_done'],
        "should have marked the message as read on clicking on the preview"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have opened the thread on clicking on the preview"
    );
});

QUnit.test('click on expand from chat window should close the chat window and open the form view', async function (assert) {
    assert.expect(8);

    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action.res_id,
            11,
            "should redirect to the id of the thread"
        );
        assert.strictEqual(
            payload.action.res_model,
            'res.partner',
            "should redirect to the model of the thread"
        );
    });
    await this.start({
        env: { bus },
        hasChatWindow: true,
    });
    const thread = this.env.models['mail.thread'].create({
        id: 11,
        model: 'res.partner',
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
        '.o_ThreadNeedactionPreview',
        "should have a preview initially"
    );
    await afterNextRender(() =>
        document.querySelector('.o_ThreadNeedactionPreview').click()
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have opened the thread on clicking on the preview"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindowHeader_commandExpand',
        "should have an expand button"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ChatWindowHeader_commandExpand').click()
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should have closed the chat window on clicking expand"
    );
    assert.verifySteps(
        ['do_action'],
        "should have done an action to open the form view"
    );
});

});
});
});

});
