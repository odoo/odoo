/** @odoo-module **/

import ThreadNeedactionPreview from '@mail/components/thread_needaction_preview/thread_needaction_preview';
import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    start,
} from '@mail/utils/test_utils';

const components = { ThreadNeedactionPreview };

QUnit.module('rating', {}, function () {
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

QUnit.test('rating value displayed on the systray', async function (assert) {
    assert.expect(3);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        is_notification: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
    });
    this.data['rating.rating'].records.push({
        rating: 5,
        message_id: 21,
        res_id: 21,
        partner_id: this.data.currentPartnerId,
        consumed: true,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview',
        "should have a ThreadNeedactionPreview in the body"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_rating_text').textContent,
        "Rating:",
        "should display the correct content (Rating:)"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_rating_image',
        "should have a rating image in the body"
    );
});

});
});
});
