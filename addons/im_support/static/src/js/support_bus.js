odoo.define('im_support.SupportBus', function (require) {
"use strict";

/**
 * This module instantiates and exports the instance of the Bus, parameterized
 * to poll the Support server.
 */

var BusService = require('bus.BusService');

var supportSession = require('im_support.SupportSession');

var { serviceRegistry } = require('web.core');

class SupportBusService extends BusService {

    /**
     * @override _makePoll to force the remote session
     */
    _makePoll(data) {
        return supportSession.rpc(this.POLL_ROUTE, data, {
            shadow : true,
            timeout: 60000,
        });
    }
}

Object.assign(SupportBusService, {
    LOCAL_STORAGE_PREFIX: 'im_support',
    POLL_ROUTE: '/longpolling/support_poll',
});

serviceRegistry.add('support_bus', SupportBusService);

return SupportBusService;

});

