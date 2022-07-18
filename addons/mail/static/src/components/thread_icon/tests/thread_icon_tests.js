/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_icon', {}, function () {
QUnit.module('thread_icon_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createThreadIcon = async thread => {
            await createRootMessagingComponent(this, "ThreadIcon", {
                props: { threadLocalId: thread.localId },
                target: this.widget.el
            });
        };

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };

    },
    afterEach() {
        afterEach(this);
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
    await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
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
        this.widget.call('bus_service', 'trigger', 'notification', [{
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
        this.widget.call('bus_service', 'trigger', 'notification', [{
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
});
