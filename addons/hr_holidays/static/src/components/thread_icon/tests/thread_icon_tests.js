/** @odoo-module **/

import {
    afterEach,
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
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
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

QUnit.test('title of thread icon of a chat when correspondent is on leave & online with a returning date', async function (assert) {
    assert.expect(1);

    const returningDate = moment.utc().add(1, 'month');
    this.data['res.partner'].records.push({
        id: 7,
        im_status: 'leave_online',
        name: "Demo",
        out_of_office_date_end: returningDate.format("YYYY-MM-DD"),
    });
    this.data['mail.channel'].records = [{
        channel_type: 'chat',
        id: 20,
        members: [this.data.currentPartnerId, 7],
    }];
    await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread);

    const formattedDate = returningDate.toDate().toLocaleDateString(
        this.messaging.locale.language.replace(/_/g, '-'),
        { day: 'numeric', month: 'short' }
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadIcon_online').getAttribute('title'),
        `Out of office until ${formattedDate} - Online`,
        'out of office message should metion the returning data and online status'
    );
});

QUnit.test('title of thread icon of a chat when correspondent is on leave & online without a returning date', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({
        id: 7,
        im_status: 'leave_online',
        name: "Demo",
    });
    this.data['mail.channel'].records = [{
        channel_type: 'chat',
        id: 20,
        members: [this.data.currentPartnerId, 7],
    }];
    await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread);

    assert.strictEqual(
        document.querySelector('.o_ThreadIcon_online').getAttribute('title'),
        'Out of office - Online',
        'out of office message should metion online status'
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
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
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

QUnit.test('title of thread icon of a chat when correspondent is on leave & away with a returning date', async function (assert) {
    assert.expect(1);

    const returningDate = moment.utc().add(1, 'month');
    this.data['res.partner'].records.push({
        id: 7,
        im_status: 'leave_away',
        name: "Demo",
        out_of_office_date_end: returningDate.format("YYYY-MM-DD"),
    });
    this.data['mail.channel'].records = [{
        channel_type: 'chat',
        id: 20,
        members: [this.data.currentPartnerId, 7],
    }];
    await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread);

    const formattedDate = returningDate.toDate().toLocaleDateString(
        this.messaging.locale.language.replace(/_/g, '-'),
        { day: 'numeric', month: 'short' }
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadIcon_away').getAttribute('title'),
        `Out of office until ${formattedDate} - Away`,
        'out of office message should metion the returning data and away status'
    );
});

QUnit.test('title of thread icon of a chat when correspondent is on leave & away without a returning date', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({
        id: 7,
        im_status: 'leave_away',
        name: "Demo",
    });
    this.data['mail.channel'].records = [{
        channel_type: 'chat',
        id: 20,
        members: [this.data.currentPartnerId, 7],
    }];
    await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread);

    assert.strictEqual(
        document.querySelector('.o_ThreadIcon_away').getAttribute('title'),
        'Out of office - Away',
        'out of office message should metion away status'
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
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
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

QUnit.test('title of thread icon of a chat when correspondent is on leave & offline with a returning date', async function (assert) {
    assert.expect(1);

    const returningDate = moment.utc().add(1, 'month');
    this.data['res.partner'].records.push({
        id: 7,
        im_status: 'leave_offline',
        name: "Demo",
        out_of_office_date_end: returningDate.format("YYYY-MM-DD"),
    });
    this.data['mail.channel'].records = [{
        channel_type: 'chat',
        id: 20,
        members: [this.data.currentPartnerId, 7],
    }];
    await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread);

    const formattedDate = returningDate.toDate().toLocaleDateString(
        this.messaging.locale.language.replace(/_/g, '-'),
        { day: 'numeric', month: 'short' }
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadIcon_offline').getAttribute('title'),
        `Out of office until ${formattedDate}`,
        'out of office message should metion the returning data'
    );
});

QUnit.test('title of thread icon of a chat when correspondent is on leave & offline without a returning date', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({
        id: 7,
        im_status: 'leave_offline',
        name: "Demo",
    });
    this.data['mail.channel'].records = [{
        channel_type: 'chat',
        id: 20,
        members: [this.data.currentPartnerId, 7],
    }];
    await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread);

    assert.strictEqual(
        document.querySelector('.o_ThreadIcon_offline').getAttribute('title'),
        'Out of office',
        'only "Out of office" should be shown'
    );
});

});
});
});
