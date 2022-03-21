/** @odoo-module **/

import { beforeEach, start } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail_bot', {}, function () {
QUnit.module('messaging_initializer_tests.js', {
    beforeEach() {
        beforeEach(this);
    },
});


QUnit.test('OdooBot initialized at init', async function (assert) {
    // TODO this test should be completed in combination with
    // implementing _mockMailChannelInitOdooBot task-2300480
    assert.expect(2);

    await start({
        data: this.data,
        env: {
            session: {
                odoobot_initialized: false,
            },
        },
        async mockRPC(route, args) {
            if (args.method === 'init_odoobot') {
                assert.step('init_odoobot');
            }
            return this._super(...arguments);
        },
    });

    assert.verifySteps(
        ['init_odoobot'],
        "should have initialized OdooBot at init"
    );
});

});
