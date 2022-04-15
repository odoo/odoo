/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_preview_tests.js');

QUnit.test('mark as read', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo" });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, {
                message_unread_counter: 1, // mandatory for good working of test, but ideally should be deduced by other server data
                partner_id: pyEnv.currentPartnerId,
            }],
            [0, 0, {
                partner_id: resPartnerId1,
            }],
        ],
    });
    const [mailMessageId1] = pyEnv['mail.message'].create([
        { author_id: resPartnerId1, model: 'mail.channel', res_id: mailChannelId1 },
        { author_id: resPartnerId1, model: 'mail.channel', res_id: mailChannelId1 },
    ]);
    const [mailChannelPartnerId] = pyEnv['mail.channel.partner'].search([['channel_id', '=', mailChannelId1], ['partner_id', '=', pyEnv.currentPartnerId]]);
    pyEnv['mail.channel.partner'].write([mailChannelPartnerId], { seen_message_id: mailMessageId1 });

    const { click, createMessagingMenuComponent } = await start({
        hasChatWindow: true,
        async mockRPC(route, args) {
            if (route.includes('set_last_seen_message')) {
                assert.step('set_last_seen_message');
            }
            return this._super(...arguments);
        },
    });
    await createMessagingMenuComponent();
    await click('.o_MessagingMenu_toggler');
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_markAsRead',
        "should have the mark as read button"
    );

    await click('.o_ThreadPreview_markAsRead');
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
        '.o_ChatWindow',
        "should not have opened the thread"
    );
});

});
});
