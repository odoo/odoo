odoo.define('mail_bot/static/src/models/messaging_initializer/messaging_initializer_tests.js', function (require) {
"use strict";

const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail_bot', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('messaging_initializer', {}, function () {
QUnit.module('messaging_initializer_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.start = async params => {
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        if (this.widget) {
            this.widget.destroy();
        }
        this.env = undefined;
        utilsAfterEach(this);
    },
});


QUnit.test('OdooBot initialized after 2 minutes', async function (assert) {
    assert.expect(3);

    await this.start({
        env: {
            session: {
                odoobot_initialized: false,
            },
        },
        hasTimeControl: true,
        async mockRPC(route, args) {
            if (args.method === 'init_odoobot') {
                assert.step('init_odoobot');
                return;
            }
            return this._super(...arguments);
        },
    });

    await this.env.testUtils.advanceTime(119 * 1000);
    assert.verifySteps(
        [],
        "should not have initialized OdooBot after 1 minute 59 seconds"
    );

    await this.env.testUtils.advanceTime(1 * 1000);
    assert.verifySteps(
        ['init_odoobot'],
        "should have initialized OdooBot after 2 minutes"
    );
});

});
});
});

});
