odoo.define('mail.messaging.component.PartnerImStatusIconTests', function (require) {
'use strict';

const components = {
    PartnerImStatusIcon: require('mail.messaging.component.PartnerImStatusIcon'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    pause,
    start: utilsStart,
} = require('mail.messaging.testUtils');

QUnit.module('mail', {}, function () {
QUnit.module('messaging', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('PartnerImStatusIcon', {
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
    const partner = this.env.entities.Partner.create({
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
    const partner = this.env.entities.Partner.create({
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
    const partner = this.env.entities.Partner.create({
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
    const partner = this.env.entities.Partner.create({
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

    partner.update({ im_status: 'offline' });
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon.o-offline`).length,
        1,
        "partner IM status icon should have offline status rendering"
    );

    partner.update({ im_status: 'away' });
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon.o-away`).length,
        1,
        "partner IM status icon should have away status rendering"
    );

    partner.update({ im_status: 'online' });
    await afterNextRender();
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
