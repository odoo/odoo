/** @odoo-module **/

/**
 * This file defines the env to use in the webclient.
 */

import commonEnv from '@web/legacy/js/common_env';
import { blockUI, unblockUI } from "@web/legacy/js/core/misc";

const env = commonEnv;
env.services = Object.assign(env.services, { blockUI, unblockUI });

export default env;
