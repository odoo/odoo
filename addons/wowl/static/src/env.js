/** @odoo-module **/
import { deployServices } from "./webclient/setup";
// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

/**
 * @typedef {Object} OdooEnv
 * @property {Object} services
 * @property {EventBus} bus
 * @property {string} debug
 * @property {(str: string) => string} _t
 * @property {boolean} [isSmall]
 */

// -----------------------------------------------------------------------------
// makeEnv
// -----------------------------------------------------------------------------

/**
 * Return a value Odoo Env object
 *
 * @param {string} debug
 * @returns {Promise<OdooEnv>}
 */
export async function makeEnv(debug) {
  const env = {
    qweb: new owl.QWeb(),
    bus: new owl.core.EventBus(),
    services: {},
    debug,
    _t: () => {
      throw new Error("Translations are not ready yet. Maybe use _lt instead?");
    },
    get isSmall() {
      throw new Error("UI service not initialized!");
    },
  };

  await deployServices(env);
  return env;
}
