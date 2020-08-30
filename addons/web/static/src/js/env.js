odoo.define("web.env", function (require) {
    "use strict";

    /**
     * This file defines the env to use in the webclient.
     */

    const commonEnv = require('web.commonEnv');
    const dataManager = require('web.data_manager');
    const { blockUI, unblockUI } = require("web.framework");

    const env = Object.assign(commonEnv, { dataManager });
    env.services = Object.assign(env.services, { blockUI, unblockUI });

    return env;
});
