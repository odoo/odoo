/** @odoo-module **/

import { afterNextRender, start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('test_mail_full', {}, function () {
QUnit.module('channel_preview_view_tests.js');

QUnit.test('rating value displayed on the thread preview', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create([
        { author_id: resPartnerId1, model: 'mail.channel', res_id: mailChannelId1 },
    ]);
    pyEnv['rating.rating'].create({
        consumed: true,
        message_id: mailMessageId1,
        partner_id: resPartnerId1,
        rating_image_url: "/rating/static/src/img/rating_5.png",
        rating_text: "top",
    });
    const { afterEvent, messaging } = await start();
    await afterNextRender(() => afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread === messaging.inbox.thread;
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ChannelPreviewView_ratingText').textContent,
        "Rating:",
        "should display the correct content (Rating:)"
    );
    assert.containsOnce(
        document.body,
        '.o_ChannelPreviewView_ratingImage',
        "should have a rating image in the body"
    );
    assert.strictEqual(
        $('.o_ChannelPreviewView_ratingImage').attr('data-src'),
        "/rating/static/src/img/rating_5.png",
        "should contain the correct rating image"
    );
    assert.strictEqual(
        $('.o_ChannelPreviewView_ratingImage').attr('data-alt'),
        "top",
        "should contain the correct rating text"
    );
});

});
