/** @odoo-module **/

import {
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_preview', {}, function () {
QUnit.module('thread_preview_tests.js', {
    beforeEach() {
        beforeEach.call(this);

        this.createThreadPreviewComponent = async props => {
            await createRootMessagingComponent(this, "ThreadPreview", {
                props,
                target: this.webClient.el,
            });
        };
    },
});

QUnit.test('mark as read', async function (assert) {
    assert.expect(8);
    this.serverData.models['mail.channel'].records.push({
        id: 11,
        message_unread_counter: 1,
    });
    this.serverData.models['mail.message'].records.push({
        id: 100,
        model: 'mail.channel',
        res_id: 11,
    });

    const { messaging } = await this.start({
        async mockRPC(route, args) {
            if (route.includes('channel_seen')) {
                assert.step('channel_seen');
            }
        },
    });
    const thread = messaging.models['mail.thread'].findFromIdentifyingData({
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
