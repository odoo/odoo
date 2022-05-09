/** @odoo-module **/

import {
    createRootMessagingComponent,
    start,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('hr_holidays', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('partner_im_status_icon_tests.js', {
    beforeEach() {
        this.createPartnerImStatusIcon = async (partner, target) => {
            await createRootMessagingComponent(partner.env, "PartnerImStatusIcon", {
                props: { partner },
                target,
            });
        };
    },
});

QUnit.test('on leave & online', async function (assert) {
    assert.expect(2);

    const { messaging, target } = await start();
    const partner = messaging.models['Partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'leave_online',
    });
    await this.createPartnerImStatusIcon(partner, target);
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

    const { messaging, target } = await start();
    const partner = messaging.models['Partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'leave_away',
    });
    await this.createPartnerImStatusIcon(partner, target);
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

    const { messaging, target } = await start();
    const partner = messaging.models['Partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'leave_offline',
    });
    await this.createPartnerImStatusIcon(partner, target);
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
