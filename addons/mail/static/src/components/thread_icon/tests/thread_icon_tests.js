/** @odoo-module **/

import {
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_icon', {}, function () {
QUnit.module('thread_icon_tests.js', {
    beforeEach() {
        beforeEach.call(this);

        this.createThreadIcon = async thread => {
            await createRootMessagingComponent(this, "ThreadIcon", {
                props: { threadLocalId: thread.localId },
                target: this.webClient.el
            });
        };
    },
});

QUnit.test('chat: correspondent is typing', async function (assert) {
    assert.expect(5);

    this.serverData.models['res.partner'].records.push({
        id: 17,
        im_status: 'online',
        name: 'Demo',
    });
    this.serverData.models['mail.channel'].records.push({
        channel_type: 'chat',
        id: 20,
        members: [this.serverData.currentPartnerId, 17],
    });
    const { messaging } = await this.start();
    const thread = messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread);

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
        const typingData = {
            info: 'typing_status',
            is_typing: true,
            partner_id: 17,
            partner_name: "Demo",
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        owl.Component.env.services.bus_service.trigger('notification', [notification]);
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
        const typingData = {
            info: 'typing_status',
            is_typing: false,
            partner_id: 17,
            partner_name: "Demo",
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        owl.Component.env.services.bus_service.trigger('notification', [notification]);
    });
    assert.containsOnce(
        document.body,
        '.o_ThreadIcon_online',
        "should have thread icon with partner im status icon 'online' (no longer typing)"
    );
});

});
});
});
