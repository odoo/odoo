odoo.define('mail/static/src/components/record_status_icon/record_status_icon_tests.js', function (require) {
'use strict';

const components = {
    RecordStatusIcon: require('mail/static/src/components/record_status_icon/record_status_icon.js'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('record_status_icon', {}, function () {
QUnit.module('record_status_icon_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createRecordStatusIcon = async (recordModel, recordLocalId, threadLocalId = undefined) => {
            const RecordStatusIconComponent = components.RecordStatusIcon;
            RecordStatusIconComponent.env = this.env;
            this.component = new RecordStatusIconComponent(null, {
                recordLocalId,
                recordModel,
                threadLocalId,
            });
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
        delete components.RecordStatusIcon.env;
    },
});

QUnit.test('partner: initially online', async function (assert) {
    assert.expect(3);

    await this.start();
    const partner = this.env.models['mail.partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'online',
    });
    await this.createRecordStatusIcon('mail.partner', partner.localId);
    assert.containsOnce(
        document.body,
        '.o_RecordStatusIcon',
        "should have partner IM status icon"
    );
    assert.strictEqual(
        document.querySelector('.o_RecordStatusIcon').dataset.recordLocalId,
        partner.localId,
        "partner IM status icon should be linked to partner with ID 7"
    );
    assert.containsOnce(
        document.body,
        '.o_RecordStatusIcon_icon.o-online',
        "partner IM status icon should have online status rendering"
    );
});

QUnit.test('partner: initially offline', async function (assert) {
    assert.expect(1);

    await this.start();
    const partner = this.env.models['mail.partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'offline',
    });
    await this.createRecordStatusIcon('mail.partner', partner.localId);
    assert.containsOnce(
        document.body,
        '.o_RecordStatusIcon_icon.o-offline',
        "partner IM status icon should have offline status rendering"
    );
});

QUnit.test('partner: initially away', async function (assert) {
    assert.expect(1);

    await this.start();
    const partner = this.env.models['mail.partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'away',
    });
    await this.createRecordStatusIcon('mail.partner', partner.localId);
    assert.strictEqual(
        document.querySelectorAll(`.o_RecordStatusIcon_icon.o-away`).length,
        1,
        "partner IM status icon should have away status rendering"
    );
});

QUnit.test('partner: change icon on change partner im_status', async function (assert) {
    assert.expect(4);

    await this.start();
    const partner = this.env.models['mail.partner'].create({
        id: 7,
        name: "Demo User",
        im_status: 'online',
    });
    await this.createRecordStatusIcon('mail.partner', partner.localId);
    assert.strictEqual(
        document.querySelectorAll(`.o_RecordStatusIcon_icon.o-online`).length,
        1,
        "partner IM status icon should have online status rendering"
    );

    await afterNextRender(() => partner.update({ im_status: 'offline' }));
    assert.strictEqual(
        document.querySelectorAll(`.o_RecordStatusIcon_icon.o-offline`).length,
        1,
        "partner IM status icon should have offline status rendering"
    );

    await afterNextRender(() => partner.update({ im_status: 'away' }));
    assert.strictEqual(
        document.querySelectorAll(`.o_RecordStatusIcon_icon.o-away`).length,
        1,
        "partner IM status icon should have away status rendering"
    );

    await afterNextRender(() => partner.update({ im_status: 'online' }));
    assert.strictEqual(
        document.querySelectorAll(`.o_RecordStatusIcon_icon.o-online`).length,
        1,
        "partner IM status icon should have online status rendering in the end"
    );
});

});
});
});

});
