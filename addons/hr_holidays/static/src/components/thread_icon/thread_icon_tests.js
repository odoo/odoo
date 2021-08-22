odoo.define('hr_holidays/static/src/components/thread_icon/thread_icon_tests.js', function (require) {
'use strict';

const {
    beforeEach,
    createRootMessagingComponent,
} = require('@mail/utils/test_utils');

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

QUnit.test('thread icon of a chat when correspondent is on leave & online', async function (assert) {
    assert.expect(2);

    this.serverData.models['res.partner'].records.push({
        id: 7,
        im_status: 'leave_online',
        name: 'Demo',
    });
     this.serverData.models['mail.channel'].records.push({
        channel_type: 'chat',
        id: 20,
        members: [this.serverData.currentPartnerId, 7],
    });
    const { messaging } = await this.start();
    const thread = messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread);

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

    this.serverData.models['res.partner'].records.push({
        id: 7,
        im_status: 'leave_away',
        name: 'Demo',
    });
     this.serverData.models['mail.channel'].records.push({
        channel_type: 'chat',
        id: 20,
        members: [this.serverData.currentPartnerId, 7],
    });
    const { messaging } = await this.start();
    const thread = messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread);

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

    this.serverData.models['res.partner'].records.push({
        id: 7,
        im_status: 'leave_offline',
        name: 'Demo',
    });
     this.serverData.models['mail.channel'].records.push({
        channel_type: 'chat',
        id: 20,
        members: [this.serverData.currentPartnerId, 7],
    });
    const { messaging } = await this.start();
    const thread = messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread);

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
});

});
