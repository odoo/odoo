/** @odoo-module **/

import {
    afterNextRender,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('messaging_menu_tests.js');

QUnit.test('livechats should be in "chat" filter', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: 'livechat',
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    await start();
    assert.containsOnce(
        document.body,
        '.o_MessagingMenu',
        "should have messaging menu"
    );

    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.containsOnce(
        document.body,
        '.o_MessagingMenuTab[data-tab-id="all"]',
        "should have a tab/filter 'all' in messaging menu"
    );
    assert.containsOnce(
        document.body,
        '.o_MessagingMenuTab[data-tab-id="chat"]',
        "should have a tab/filter 'chat' in messaging menu"
    );
    assert.hasClass(
        document.querySelector('.o_MessagingMenuTab[data-tab-id="all"]'),
        'o-active',
        "tab/filter 'all' of messaging menu should be active initially"
    );
    assert.containsOnce(
        document.body,
        `.o_ChannelPreviewView[data-channel-id="${mailChannelId1}"]`,
        "livechat should be listed in 'all' tab/filter of messaging menu"
    );

    await afterNextRender(() =>
        document.querySelector('.o_MessagingMenuTab[data-tab-id="chat"]').click()
    );
    assert.hasClass(
        document.querySelector('.o_MessagingMenuTab[data-tab-id="chat"]'),
        'o-active',
        "tab/filter 'chat' of messaging menu should become active after click"
    );
    assert.containsOnce(
        document.body,
        `.o_ChannelPreviewView[data-channel-id="${mailChannelId1}"]`,
        "livechat should be listed in 'chat' tab/filter of messaging menu"
    );
});

});
});
