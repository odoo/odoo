odoo.define('hr_holidays/static/src/components/thread_icon/thread_icon_tests.js', function (require) {
'use strict';

const components = {
    ThreadIcon: require('mail/static/src/components/thread_icon/thread_icon.js'),
};
const {
    afterEach,
    beforeEach,
    createRootComponent,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_icon', {}, function () {
QUnit.module('thread_icon_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createThreadIcon = async thread => {
            await createRootComponent(this, components.ThreadIcon, {
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
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
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
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
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
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
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
