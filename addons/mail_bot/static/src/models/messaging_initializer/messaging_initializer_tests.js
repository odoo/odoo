/** @odoo-module **/

import { beforeEach } from '@mail/utils/test_utils';

QUnit.module('mail_bot', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('messaging_initializer', {}, function () {
QUnit.module('messaging_initializer_tests.js', { beforeEach });

QUnit.skip('OdooBot initialized at init', async function (assert) {
    // skip: need to import session directly?
    // TODO this test should be completed in combination with
    // implementing _mockMailChannelInitOdooBot task-2300480
    assert.expect(2);

    await this.start({
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
});
});
