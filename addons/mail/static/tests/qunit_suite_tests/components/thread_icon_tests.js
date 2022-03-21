/** @odoo-module **/

import {
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
    start,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_icon_tests.js', {
    async beforeEach() {
        await beforeEach(this);

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

    this.data['res.partner'].records.push({
        id: 17,
        im_status: 'online',
        name: 'Demo',
    });
    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 20,
        members: [this.data.currentPartnerId, 17],
    });
    const { messaging, widget } = await start({ data: this.data });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: 20,
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
                channel_id: 20,
                is_typing: true,
                partner_id: 17,
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
                channel_id: 20,
                is_typing: false,
                partner_id: 17,
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
