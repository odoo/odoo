/** @odoo-module **/

import {
    afterNextRender,
    beforeEach,
    start,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('chat_window_manager', {}, function () {
QUnit.module('chat_window_manager_tests.js', {
    async beforeEach() {
        await beforeEach(this);
    },
});

QUnit.test('closing a chat window with no message from admin side unpins it', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({ id: 10, name: "Demo" });
    this.data['res.users'].records.push({
        id: 42,
        partner_id: 10,
    });
    this.data['mail.channel'].records.push(
        {
            channel_type: "livechat",
            id: 10,
            is_pinned: true,
            members: [this.data.currentPartnerId, 10],
            uuid: 'channel-10-uuid',
        },
    );
    const { createMessagingMenuComponent, env } = await start({ data: this.data, hasChatWindow: true });
    await createMessagingMenuComponent();

    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() => document.querySelector(`.o_NotificationList_preview`).click());
    await afterNextRender(() => document.querySelector(`.o_ChatWindowHeader_commandClose`).click());
    const channels = await env.services.rpc({
        model: 'mail.channel',
        method: 'read',
        args: [10],
    }, { shadow: true });
    assert.strictEqual(
        channels[0].is_pinned,
        false,
        'Livechat channel should not be pinned',
    );
});

});
});
});
