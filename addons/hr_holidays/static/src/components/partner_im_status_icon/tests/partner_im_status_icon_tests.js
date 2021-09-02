/** @odoo-module **/

import {
    afterEach,
    beforeEach,
    createRootMessagingComponent,
    start,
} from '@mail/utils/test_utils';

QUnit.module('hr_holidays', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('partner_im_status_icon', {}, function () {
QUnit.module('partner_im_status_icon_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createPartnerImStatusIcon = async partner => {
            await createRootMessagingComponent(this, "PartnerImStatusIcon", {
                props: { partnerLocalId: partner.localId },
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

QUnit.test('on leave & online', async function (assert) {
    assert.expect(2);

    await this.start();
    const partner = this.messaging.models['mail.partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'leave_online',
    });
    await this.createPartnerImStatusIcon(partner);
    assert.hasClass(
        document.querySelector('.o_PartnerImStatusIcon_icon'),
        'o-online',
        "partner IM status icon should have online status rendering"
    );
    assert.hasClass(
        document.querySelector('.o_PartnerImStatusIcon_icon'),
        'fa-plane',
        "partner IM status icon should have leave status rendering"
    );
});

QUnit.test('title of the icon on leave & online with a returning date', async function (assert) {
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
    const partner = this.messaging.models['mail.partner'].findFromIdentifyingData({ id: 7 });
    await this.createPartnerImStatusIcon(partner);

    const formattedDate = returningDate.toDate().toLocaleDateString(
        this.messaging.locale.language.replace(/_/g, '-'),
        { day: 'numeric', month: 'short' }
    );
    assert.strictEqual(
        document.querySelector('.o_PartnerImStatusIcon_icon').getAttribute('title'),
        `Out of office until ${formattedDate} - Online`,
        'out of office message should metion the returning data and online status'
    );
});

QUnit.test('title of the icon on leave & online without a returning date', async function (assert) {
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
    const partner = this.messaging.models['mail.partner'].findFromIdentifyingData({ id: 7 });
    await this.createPartnerImStatusIcon(partner);

    assert.strictEqual(
        document.querySelector('.o_PartnerImStatusIcon_icon').getAttribute('title'),
        'Out of office - Online',
        'out of office message should metion online status'
    );
});

QUnit.test('on leave & away', async function (assert) {
    assert.expect(2);

    await this.start();
    const partner = this.messaging.models['mail.partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'leave_away',
    });
    await this.createPartnerImStatusIcon(partner);
    assert.hasClass(
        document.querySelector('.o_PartnerImStatusIcon_icon'),
        'o-away',
        "partner IM status icon should have away status rendering"
    );
    assert.hasClass(
        document.querySelector('.o_PartnerImStatusIcon_icon'),
        'fa-plane',
        "partner IM status icon should have leave status rendering"
    );
});

QUnit.test('title of the icon on leave & away with a returning date', async function (assert) {
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
    const partner = this.messaging.models['mail.partner'].findFromIdentifyingData({ id: 7 });
    await this.createPartnerImStatusIcon(partner);

    const formattedDate = returningDate.toDate().toLocaleDateString(
        this.messaging.locale.language.replace(/_/g, '-'),
        { day: 'numeric', month: 'short' }
    );
    assert.strictEqual(
        document.querySelector('.o_PartnerImStatusIcon_icon').getAttribute('title'),
        `Out of office until ${formattedDate} - Away`,
        'out of office message should metion the returning data and away status'
    );
});

QUnit.test('title of the icon on leave & away without a returning date', async function (assert) {
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
    const partner = this.messaging.models['mail.partner'].findFromIdentifyingData({ id: 7 });
    await this.createPartnerImStatusIcon(partner);

    assert.strictEqual(
        document.querySelector('.o_PartnerImStatusIcon_icon').getAttribute('title'),
        'Out of office - Away',
        'out of office message should metion away status'
    );
});

QUnit.test('on leave & offline', async function (assert) {
    assert.expect(2);

    await this.start();
    const partner = this.messaging.models['mail.partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'leave_offline',
    });
    await this.createPartnerImStatusIcon(partner);
    assert.hasClass(
        document.querySelector('.o_PartnerImStatusIcon_icon'),
        'o-offline',
        "partner IM status icon should have offline status rendering"
    );
    assert.hasClass(
        document.querySelector('.o_PartnerImStatusIcon_icon'),
        'fa-plane',
        "partner IM status icon should have leave status rendering"
    );
});

QUnit.test('title of the icon on leave & offline with a returning date', async function (assert) {
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
    const partner = this.messaging.models['mail.partner'].findFromIdentifyingData({ id: 7 });
    await this.createPartnerImStatusIcon(partner);

    const formattedDate = returningDate.toDate().toLocaleDateString(
        this.messaging.locale.language.replace(/_/g, '-'),
        { day: 'numeric', month: 'short' }
    );
    assert.strictEqual(
        document.querySelector('.o_PartnerImStatusIcon_icon').getAttribute('title'),
        `Out of office until ${formattedDate}`,
        'out of office message should metion the returning data'
    );
});

QUnit.test('title of the icon on leave & offline without a returning date', async function (assert) {
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
    const partner = this.messaging.models['mail.partner'].findFromIdentifyingData({ id: 7 });
    await this.createPartnerImStatusIcon(partner);

    assert.strictEqual(
        document.querySelector('.o_PartnerImStatusIcon_icon').getAttribute('title'),
        'Out of office',
        'only "Out of office" should be shown'
    );
});

});
});
});
