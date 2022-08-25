odoo.define('point_of_sale.test_env', async function (require) {
    'use strict';

    /**
     * Many components in PoS are dependent on the PosGlobalState instance (pos).
     * Therefore, for unit tests that require pos in the Components' env, we
     * prepared here a test env maker (makePosTestEnv) based on
     * makeTestEnvironment of web.
     */

    const makeTestEnvironment = require('web.test_env');
    const env = require('point_of_sale.env');
    const { PosGlobalState } = require('point_of_sale.models');
    const cleanup = require("@web/../tests/helpers/cleanup");

    // We override this method in the pos unit tests to prevent the unnecessary error in the web tests.
    cleanup.registerCleanup = () => {}

    await env.session.is_bound;
    const pos = PosGlobalState.create({ env });
    await pos.load_server_data();

    /**
     * @param {Object} env default env
     * @param {Function} providedRPC mock rpc
     * @param {Function} providedDoAction mock do_action
     */
    function makePosTestEnv(env = {}, providedRPC = null, providedDoAction = null) {
        env = Object.assign(env, { pos });
        return makeTestEnvironment(env, providedRPC);
    }

    return makePosTestEnv;
});
