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

});
});
});
