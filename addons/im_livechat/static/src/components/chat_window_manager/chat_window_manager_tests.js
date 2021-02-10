odoo.define('im_livechat/static/src/components/chat_window_manager/chat_window_manager_tests.js', function (require) {
'use strict';

const {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('chat_window_manager', {}, function () {
QUnit.module('chat_window_manager_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const { afterEvent, env, widget } = await start(Object.assign(
                { hasChatWindow: true, hasMessagingMenu: true },
                params,
                { data: this.data }
            ));
            this.debug = params && params.debug;
            this.afterEvent = afterEvent;
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
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
    await this.start();

    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() => document.querySelector(`.o_NotificationList_preview`).click());
    await afterNextRender(() => document.querySelector(`.o_ChatWindowHeader_commandClose`).click());
    const channels = await this.env.services.rpc({
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

});
