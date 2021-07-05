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

QUnit.test('rating value displayed on the thread needaction preview', async function (assert) {
    assert.expect(3);
    this.data['mail.message'].records.push({
        id: 21,
        is_notification: true,
        model: 'res.partner',
        needaction_partner_ids: [this.data.currentPartnerId],
        needaction: true,
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
    });
    this.data['rating.rating'].records.push({
        consumed: true,
        message_id: 21,
        partner_id: this.data.currentPartnerId,
        rating: 5,
        res_id: 21,
    });
    await this.start({ hasMessagingMenu: true, });
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_ratingText').textContent,
        "Rating:",
        "should display the correct content (Rating:)"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_ratingImage',
        "should have a rating image in the body"
    );
    assert.strictEqual(
        $('.o_ThreadNeedactionPreview_ratingImage').attr('data-src'),
        "/rating/static/src/img/rating_5.png",
        "should cantain the correct content (Rating:)"
    );
});

});
});
});
