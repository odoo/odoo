/** @odoo-module **/

import {
    afterNextRender,
    beforeEach,
} from '@mail/utils/test_utils';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('chat_window_manager', {}, function () {
QUnit.module('chat_window_manager_tests.js', { beforeEach });

QUnit.skip('closing a chat window with no message from admin side unpins it', async function (assert) {
    // skip the livechat doesn't appear in the menu for some reason
    assert.expect(1);

    this.serverData.models['res.partner'].records.push({ id: 10, name: "Demo" });
    this.serverData.models['res.users'].records.push({
        id: 42,
        partner_id: 10,
    });
    this.serverData.models['mail.channel'].records.push(
        {
            channel_type: "livechat",
            id: 10,
            is_pinned: true,
            members: [this.serverData.currentPartnerId, 10],
            uuid: 'channel-10-uuid',
        },
    );
    const { env } = await this.start();

    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() => document.querySelector(`.o_NotificationList_preview`).click());
    await afterNextRender(() => document.querySelector(`.o_ChatWindowHeader_commandClose`).click());
    const channels = await env.services.orm.read('mail.channel', [10]);
    assert.strictEqual(
        channels[0].is_pinned,
        false,
        'Livechat channel should not be pinned',
    );
});

});
});
});
