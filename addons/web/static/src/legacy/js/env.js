/** @odoo-module alias=web.env **/

/**
 * This file defines the env to use in the webclient.
 */

import commonEnv from 'web.commonEnv';
import dataManager from 'web.data_manager';
import { blockUI, unblockUI } from "web.framework";

const env = Object.assign(commonEnv, { dataManager });
env.services = Object.assign(env.services, { blockUI, unblockUI });

export default env;
