/** @odoo-module **/

import {
    afterNextRender,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_icon_tests.js');

QUnit.test('chat: correspondent is typing', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        im_status: 'online',
        name: 'Demo',
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: 'chat',
    });
    const { openDiscuss } = await start();
    await openDiscuss();

    assert.containsOnce(
        document.body.querySelector('.o_DiscussSidebarCategoryItem'),
        '.o_ThreadIcon',
        "should have thread icon in the sidebar"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadIcon_online',
        "should have thread icon with persona IM status icon 'online'"
    );

    const mailChannel1 = pyEnv['mail.channel'].searchRead([['id', '=', mailChannelId1]])[0];
    // simulate receive typing notification from demo "is typing"
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(mailChannel1, 'mail.channel.member/typing_status', {
            'channel_id': mailChannelId1,
            'is_typing': true,
            'partner_id': resPartnerId1,
            'partner_name': "Demo",
        });
    });
    assert.containsOnce(
        document.body,
        '.o_ThreadIcon_typing',
        "should have thread icon with partner currently typing"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadIcon_typing').title,
        "Demo is typing...",
        "title of icon should tell demo is currently typing"
    );

    // simulate receive typing notification from demo "no longer is typing"
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(mailChannel1, 'mail.channel.member/typing_status', {
            'channel_id': mailChannelId1,
            'is_typing': false,
            'partner_id': resPartnerId1,
            'partner_name': "Demo",
        });
    });
    assert.containsOnce(
        document.body,
        '.o_ThreadIcon_online',
        "should have thread icon with persona IM status icon 'online' (no longer typing)"
    );
});

});
});
