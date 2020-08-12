odoo.define('mail_bot/static/src/models/messaging_initializer/messaging_initializer_tests.js', function (require) {
"use strict";

const { afterEach, beforeEach, start } = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail_bot', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('messaging_initializer', {}, function () {
QUnit.module('messaging_initializer_tests.js', {
    beforeEach() {
        beforeEach(this);

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


QUnit.test('OdooBot initialized after 2 minutes', async function (assert) {
    // TODO this test should be completed in combination with
    // implementing _mockMailChannelInitOdooBot task-2300480
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
