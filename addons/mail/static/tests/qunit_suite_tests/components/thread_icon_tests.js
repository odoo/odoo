/** @odoo-module **/

import {
    afterNextRender,
    createRootMessagingComponent,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_icon_tests.js', {
    async beforeEach() {
        this.createThreadIcon = async (thread, target) => {
            await createRootMessagingComponent(thread.env, "ThreadIcon", {
                props: { threadLocalId: thread.localId },
                target,
            });
        };
    },
});

QUnit.test('chat: correspondent is typing', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        im_status: 'online',
        name: 'Demo',
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: 'chat',
    });
    const { messaging, widget } = await start();
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread, widget.el);

    assert.containsOnce(
        document.body,
        '.o_ThreadIcon',
        "should have thread icon"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadIcon_online',
        "should have thread icon with partner im status icon 'online'"
    );

    // simulate receive typing notification from demo "is typing"
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/typing_status',
            payload: {
                channel_id: mailChannelId1,
                is_typing: true,
                partner_id: resPartnerId1,
                partner_name: "Demo",
            },
        }]);
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
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/typing_status',
            payload: {
                channel_id: mailChannelId1,
                is_typing: false,
                partner_id: resPartnerId1,
                partner_name: "Demo",
            },
        }]);
    });
    assert.containsOnce(
        document.body,
        '.o_ThreadIcon_online',
        "should have thread icon with partner im status icon 'online' (no longer typing)"
    );
});

});
});
