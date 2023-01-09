/** @odoo-module */
// FIXME unused module?
/**
 * Many components in PoS are dependent on the PosGlobalState instance (pos).
 * Therefore, for unit tests that require pos in the Components' env, we
 * prepared here a test env maker (makePosTestEnv) based on
 * makeTestEnvironment of web.
 */

import makeTestEnvironment from "web.test_env";
import env from "@point_of_sale/js/pos_env";
import { PosGlobalState } from "@point_of_sale/js/models";

// eslint-disable-next-line no-undef
const cleanup = require("@web/../tests/helpers/cleanup");
// We override this method in the pos unit tests to prevent the unnecessary error in the web tests.
// FIXME: this is bonkers, we're overriding which method is exported by the module, this is super
// sensitive to load order. STOP DOING THIS ASAP.
cleanup.registerCleanup = () => {};

const makePosTestEnv = env.session.is_bound
    .then(() => {
        const pos = PosGlobalState.create({ env });
        return pos.load_server_data().then(() => pos);
    })
    .then((pos) => {
        /**
         * @param {Object} env default env
         * @param {Function} providedRPC mock rpc
         * @param {Function} providedDoAction mock do_action
         */
        return function makePosTestEnv(env = {}, providedRPC = null, providedDoAction = null) {
            env = Object.assign(env, { pos });
            return makeTestEnvironment(env, providedRPC);
        };
    });

export default makePosTestEnv;
