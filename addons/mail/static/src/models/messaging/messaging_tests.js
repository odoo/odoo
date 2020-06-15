odoo.define('mail/static/src/models/messaging/messaging_tests.js', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('messaging', {}, function () {
QUnit.module('messaging_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            const { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        this.env = undefined;
        if (this.widget) {
            this.widget.destroy();
            this.widget = undefined;
        }
    },
});

QUnit.test('currentPartner initialized from session', async function (assert) {
    assert.expect(5);

    await this.start();

    assert.ok(this.env.messaging.currentPartner);
    assert.strictEqual(
        this.env.messaging.currentPartner.id,
        this.env.session.partner_id
    );
    assert.strictEqual(
        this.env.messaging.currentPartner.name,
        this.env.session.name
    );
    assert.strictEqual(
        this.env.messaging.currentPartner.display_name,
        this.env.session.partner_display_name
    );
    assert.strictEqual(
        this.env.messaging.currentPartner.user.id,
        this.env.session.uid
    );
});

});
});
});

});
