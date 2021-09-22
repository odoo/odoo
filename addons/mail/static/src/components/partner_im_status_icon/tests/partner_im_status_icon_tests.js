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

QUnit.test('initially online', async function (assert) {
    assert.expect(3);

    await this.start();
    const partner = this.messaging.models['mail.partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'online',
    });
    await this.createPartnerImStatusIcon(partner);
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon`).length,
        1,
        "should have partner IM status icon"
    );
    assert.strictEqual(
        document.querySelector(`.o_PartnerImStatusIcon`).dataset.partnerLocalId,
        partner.localId,
        "partner IM status icon should be linked to partner with ID 7"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon.o-online`).length,
        1,
        "partner IM status icon should have online status rendering"
    );
});

QUnit.test('initially offline', async function (assert) {
    assert.expect(1);

    await this.start();
    const partner = this.messaging.models['mail.partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'offline',
    });
    await this.createPartnerImStatusIcon(partner);
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon.o-offline`).length,
        1,
        "partner IM status icon should have offline status rendering"
    );
});

QUnit.test('initially away', async function (assert) {
    assert.expect(1);

    await this.start();
    const partner = this.messaging.models['mail.partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'away',
    });
    await this.createPartnerImStatusIcon(partner);
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon.o-away`).length,
        1,
        "partner IM status icon should have away status rendering"
    );
});

QUnit.test('change icon on change partner im_status', async function (assert) {
    assert.expect(4);

    await this.start();
    const partner = this.messaging.models['mail.partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'online',
    });
    await this.createPartnerImStatusIcon(partner);
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon.o-online`).length,
        1,
        "partner IM status icon should have online status rendering"
    );

    await afterNextRender(() => partner.update({ im_status: 'offline' }));
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon.o-offline`).length,
        1,
        "partner IM status icon should have offline status rendering"
    );

    await afterNextRender(() => partner.update({ im_status: 'away' }));
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon.o-away`).length,
        1,
        "partner IM status icon should have away status rendering"
    );

    await afterNextRender(() => partner.update({ im_status: 'online' }));
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon.o-online`).length,
        1,
        "partner IM status icon should have online status rendering in the end"
    );
});

});
});
});
