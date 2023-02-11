odoo.define('point_of_sale.test_env', async function (require) {
    'use strict';

    /**
     * Many components in PoS are dependent on the PosModel instance (pos).
     * Therefore, for unit tests that require pos in the Components' env, we
     * prepared here a test env maker (makePosTestEnv) based on
     * makeTestEnvironment of web.
     */

    const makeTestEnvironment = require('web.test_env');
    const env = require('web.env');
    const models = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    Registries.Component.add(owl.misc.Portal);

    await env.session.is_bound;
    const pos = new models.PosModel({
        rpc: env.services.rpc,
        session: env.session,
        do_action: async () => {},
        setLoadingMessage: () => {},
        setLoadingProgress: () => {},
        showLoadingSkip: () => {},
    });
    await pos.ready;

    /**
     * @param {Object} env default env
     * @param {Function} providedRPC mock rpc
     * @param {Function} providedDoAction mock do_action
     */
    function makePosTestEnv(env = {}, providedRPC = null, providedDoAction = null) {
        env = Object.assign(env, { pos });
        let posEnv = makeTestEnvironment(env, providedRPC);
        // Replace rpc in the PosModel instance after loading
        // data from the server so that every succeeding rpc calls
        // made by pos are mocked by the providedRPC.
        pos.rpc = posEnv.rpc;
        pos.do_action = providedDoAction;
        return posEnv;
    }

    return makePosTestEnv;
});
