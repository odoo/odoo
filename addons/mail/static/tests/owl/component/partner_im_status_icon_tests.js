odoo.define('mail.component.PartnerImStatusIconTests', function (require) {
'use strict';

const PartnerImStatusIcon = require('mail.component.PartnerImStatusIcon');
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    pause,
    start: utilsStart,
} = require('mail.messagingTestUtils');

QUnit.module('mail.messaging', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('PartnerImStatusIcon', {
    beforeEach() {
        utilsBeforeEach(this);
        this.createPartnerImStatusIcon = async partnerLocalId => {
            PartnerImStatusIcon.env = this.env;
            this.partnerImStatusIcon = new PartnerImStatusIcon(null, { partnerLocalId });
            await this.partnerImStatusIcon.mount(this.widget.$el[0]);
        };
        this.start = async params => {
            if (this.wiget) {
                this.widget.destroy();
            }
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.partnerImStatusIcon) {
            this.partnerImStatusIcon.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.env = undefined;
        delete PartnerImStatusIcon.env;
    }
});

QUnit.test('initially online', async function (assert) {
    assert.expect(3);

    await this.start();
    const partnerLocalId = this.env.store.dispatch('_createPartner', {
        id: 7,
        name: "Demo User",
        im_status: 'online',
    });
    await this.createPartnerImStatusIcon(partnerLocalId);
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon`).length,
        1,
        "should have partner IM status icon"
    );
    assert.strictEqual(
        document.querySelector(`.o_PartnerImStatusIcon`).dataset.partnerLocalId,
        'res.partner_7',
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
    const partnerLocalId = this.env.store.dispatch('_createPartner', {
        id: 7,
        name: "Demo User",
        im_status: 'offline',
    });
    await this.createPartnerImStatusIcon(partnerLocalId);
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon.o-offline`).length,
        1,
        "partner IM status icon should have offline status rendering"
    );
});

QUnit.test('initially away', async function (assert) {
    assert.expect(1);

    await this.start();
    const partnerLocalId = this.env.store.dispatch('_createPartner', {
        id: 7,
        name: "Demo User",
        im_status: 'away',
    });
    await this.createPartnerImStatusIcon(partnerLocalId);
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon.o-away`).length,
        1,
        "partner IM status icon should have away status rendering"
    );
});

QUnit.test('change icon on change partner im_status', async function (assert) {
    assert.expect(4);

    await this.start();

    const partnerLocalId = this.env.store.dispatch('_createPartner', {
        id: 7,
        name: "Demo User",
        im_status: 'online',
    });
    await this.createPartnerImStatusIcon(partnerLocalId);
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon.o-online`).length,
        1,
        "partner IM status icon should have online status rendering"
    );

    this.env.store.dispatch('_updatePartner', 'res.partner_7', { im_status: 'offline' });
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon.o-offline`).length,
        1,
        "partner IM status icon should have offline status rendering"
    );

    this.env.store.dispatch('_updatePartner', 'res.partner_7', { im_status: 'away' });
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon.o-away`).length,
        1,
        "partner IM status icon should have away status rendering"
    );

    this.env.store.dispatch('_updatePartner', 'res.partner_7', { im_status: 'online' });
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
