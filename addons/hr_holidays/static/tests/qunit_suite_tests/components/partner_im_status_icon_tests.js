/** @odoo-module **/

import { start } from '@mail/../tests/helpers/test_utils';

QUnit.module('hr_holidays', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('partner_im_status_icon_tests.js');

QUnit.test('on leave & online', async function (assert) {
    assert.expect(2);

    const { createRootMessagingComponent, messaging } = await start();
    const partner = messaging.models['Partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'leave_online',
    });
    await createRootMessagingComponent('PartnerImStatusIcon', { partner });
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

    const { createRootMessagingComponent, messaging } = await start();
    const partner = messaging.models['Partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'leave_away',
    });
    await createRootMessagingComponent('PartnerImStatusIcon', { partner });
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

    const { createRootMessagingComponent, messaging } = await start();
    const partner = messaging.models['Partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'leave_offline',
    });
    await createRootMessagingComponent('PartnerImStatusIcon', { partner });
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
