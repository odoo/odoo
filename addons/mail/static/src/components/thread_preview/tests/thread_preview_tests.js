/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_preview', {}, function () {
QUnit.module('thread_preview_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createThreadPreviewComponent = async props => {
            await createRootMessagingComponent(this, "ThreadPreview", {
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

QUnit.test('mark as read', async function (assert) {
    assert.expect(8);
    this.data['mail.channel'].records.push({
        id: 11,
        message_unread_counter: 1,
    });
    this.data['mail.message'].records.push({
        id: 100,
        model: 'mail.channel',
        res_id: 11,
    });

    await this.start({
        hasChatWindow: true,
        async mockRPC(route, args) {
            if (route.includes('set_last_seen_message')) {
                assert.step('set_last_seen_message');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
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
        ['set_last_seen_message'],
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
