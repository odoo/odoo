/** @odoo-module **/

import { ThreadPreview } from '@mail/components/thread_preview/thread_preview';
import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    start,
} from '@mail/utils/test_utils';

const components = { ThreadPreview };

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

QUnit.test('rendering of tracking value displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Total",
        field_type: "integer",
        new_value: 0,
        old_value: 1,
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Total:10",
        "should display the correct content of tracked field: from non-0 to 0 (Total: 1 -> 0)"
    );
});

});
});
});
