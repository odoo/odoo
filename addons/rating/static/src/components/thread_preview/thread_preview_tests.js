/** @odoo-module **/

import ThreadPreview from '@mail/components/thread_preview/thread_preview';
import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    start,
} from '@mail/utils/test_utils';

const components = { ThreadPreview };

QUnit.module('rating', {}, function () {
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

QUnit.test('rating value displayed on the thread preview', async function (assert) {
    assert.expect(3);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['rating.rating'].records.push({
        consumed: true,
        message_id: 21,
        partner_id: this.data.currentPartnerId,
        rating: 5,
        res_id: 21,
    });
    await this.start({ hasMessagingMenu: true, });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_ratingText').textContent,
        "Rating:",
        "should display the correct content (Rating:)"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_ratingImage',
        "should have a rating image in the body"
    );
    assert.strictEqual(
        $('.o_ThreadPreview_ratingImage').attr('data-src'),
        "/rating/static/src/img/rating_5.png",
        "should cantain the correct content (Rating:)"
    );
});

});
});
});
