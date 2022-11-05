/** @odoo-module **/

import { afterNextRender, start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('notification_list_tests.js');

QUnit.test('marked as read thread notifications are ordered by last message date', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([
        { name: "Channel 2019" },
        { name: "Channel 2020" },
    ]);
    pyEnv['mail.message'].create([
        {
            date: "2019-01-01 00:00:00",
            model: 'mail.channel',
            res_id: mailChannelId1,
        },
        {
            date: "2020-01-01 00:00:00",
            model: 'mail.channel',
            res_id: mailChannelId2,
        },
    ]);
    const { click } = await start();
    await click('.o_MessagingMenu_toggler');
    assert.containsN(
        document.body,
        '.o_ChannelPreviewView',
        2,
        "there should be two thread previews"
    );
    const channelPreviewViewElList = document.querySelectorAll('.o_ChannelPreviewView');
    assert.strictEqual(
        channelPreviewViewElList[0].querySelector(':scope .o_ChannelPreviewView_name').textContent,
        'Channel 2020',
        "First channel in the list should be the channel of 2020 (more recent last message)"
    );
    assert.strictEqual(
        channelPreviewViewElList[1].querySelector(':scope .o_ChannelPreviewView_name').textContent,
        'Channel 2019',
        "Second channel in the list should be the channel of 2019 (least recent last message)"
    );
});

QUnit.test('thread notifications are re-ordered on receiving a new message', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([
        { name: "Channel 2019" },
        { name: "Channel 2020" },
    ]);
    pyEnv['mail.message'].create([
        {
            date: "2019-01-01 00:00:00",
            model: 'mail.channel',
            res_id: mailChannelId1,
        },
        {
            date: "2020-01-01 00:00:00",
            model: 'mail.channel',
            res_id: mailChannelId2,
        },
    ]);
    const { click } = await start();
    await click('.o_MessagingMenu_toggler');
    assert.containsN(
        document.body,
        '.o_ChannelPreviewView',
        2,
        "there should be two thread previews"
    );

    const mailChannel1 = pyEnv['mail.channel'].searchRead([['id', '=', mailChannelId1]])[0];
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(mailChannel1, 'mail.channel/new_message', {
            'id': mailChannelId1,
            'message': {
                author_id: [7, "Demo User"],
                body: "<p>New message !</p>",
                date: "2020-03-23 10:00:00",
                id: 44,
                message_type: 'comment',
                model: 'mail.channel',
                record_name: 'Channel 2019',
                res_id: mailChannelId1,
            },
        });
    });
    assert.containsN(
        document.body,
        '.o_ChannelPreviewView',
        2,
        "there should still be two thread previews"
    );
    const channelPreviewViewElList = document.querySelectorAll('.o_ChannelPreviewView');
    assert.strictEqual(
        channelPreviewViewElList[0].querySelector(':scope .o_ChannelPreviewView_name').textContent,
        'Channel 2019',
        "First channel in the list should now be 'Channel 2019'"
    );
    assert.strictEqual(
        channelPreviewViewElList[1].querySelector(':scope .o_ChannelPreviewView_name').textContent,
        'Channel 2020',
        "Second channel in the list should now be 'Channel 2020'"
    );
});

});
});
