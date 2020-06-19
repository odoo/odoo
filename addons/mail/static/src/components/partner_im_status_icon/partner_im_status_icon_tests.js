odoo.define('mail/static/src/components/partner_im_status_icon/partner_im_status_icon_tests.js', function (require) {
'use strict';

const components = {
    PartnerImStatusIcon: require('mail/static/src/components/partner_im_status_icon/partner_im_status_icon.js'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('partner_im_status_icon', {}, function () {
QUnit.module('partner_im_status_icon_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createPartnerImStatusIcon = async partner => {
            const PartnerImStatusIconComponent = components.PartnerImStatusIcon;
            PartnerImStatusIconComponent.env = this.env;
            this.component = new PartnerImStatusIconComponent(null, { partnerLocalId: partner.localId });
            await this.component.mount(this.widget.el);
        };

        this.start = async params => {
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.component) {
            this.component.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.env = undefined;
        delete components.PartnerImStatusIcon.env;
    },
});

QUnit.test('initially online', async function (assert) {
    assert.expect(3);

    await this.start();
    const partner = this.env.models['mail.partner'].create({
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
    const partner = this.env.models['mail.partner'].create({
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
    const partner = this.env.models['mail.partner'].create({
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
    const partner = this.env.models['mail.partner'].create({
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

});
