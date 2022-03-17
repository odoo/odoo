/** @odoo-module **/

import {
    beforeEach,
    createRootMessagingComponent,
    start,
} from '@mail/utils/test_utils';

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

QUnit.test('thread icon of a chat when correspondent is on leave & online', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records.push({
        id: 7,
        im_status: 'leave_online',
        name: 'Demo',
    });
     this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 20,
        members: [this.data.currentPartnerId, 7],
    });
    const { messaging, widget } = await start({ data: this.data });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread, widget.el);

    assert.containsOnce(
        document.body,
        '.o_ThreadIcon_online',
        "thread icon should have online status rendering"
    );
    assert.hasClass(
        document.querySelector('.o_ThreadIcon_online'),
        'fa-plane',
        "thread icon should have leave status rendering"
    );
});

QUnit.test('thread icon of a chat when correspondent is on leave & away', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records.push({
        id: 7,
        im_status: 'leave_away',
        name: 'Demo',
    });
     this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 20,
        members: [this.data.currentPartnerId, 7],
    });
    const { messaging, widget } = await start({ data: this.data });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread, widget.el);

    assert.containsOnce(
        document.body,
        '.o_ThreadIcon_away',
        "thread icon should have away status rendering"
    );
    assert.hasClass(
        document.querySelector('.o_ThreadIcon_away'),
        'fa-plane',
        "thread icon should have leave status rendering"
    );
});

QUnit.test('thread icon of a chat when correspondent is on leave & offline', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records.push({
        id: 7,
        im_status: 'leave_offline',
        name: 'Demo',
    });
     this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 20,
        members: [this.data.currentPartnerId, 7],
    });
    const { messaging, widget } = await start({ data: this.data });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread, widget.el);

    assert.containsOnce(
        document.body,
        '.o_ThreadIcon_offline',
        "thread icon should have offline status rendering"
    );
    assert.hasClass(
        document.querySelector('.o_ThreadIcon_offline'),
        'fa-plane',
        "thread icon should have leave status rendering"
    );
});

});
});
