/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

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

QUnit.test('rating value displayed on the systray', async function (assert) {
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
        rating: 5,
        message_id: 21,
        res_id: 21,
        partner_id: this.data.currentPartnerId,
        consumed: true,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview',
        "should have a ThreadNeedactionPreview in the body"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_rating_text').textContent,
        "Rating:",
        "should display the correct content (Rating:)"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_rating_image',
        "should have a rating image in the body"
    );
});

});
});
});
