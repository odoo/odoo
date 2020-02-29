odoo.define('im_support.SupportBus', function (require) {
"use strict";

/**
 * This module instantiates and exports the instance of the Bus, parameterized
 * to poll the Support server.
 */

var BusService = require('bus.BusService');
var supportSession = require('im_support.SupportSession');
var core = require('web.core');

var SupportBusService =  BusService.extend({
    LOCAL_STORAGE_PREFIX: 'im_support',
    POLL_ROUTE: '/longpolling/support_poll',

    /**
     * @override _makePoll to force the remote session
     */
    _makePoll: function(data) {
        return supportSession.rpc(this.POLL_ROUTE, data, {shadow : true, timeout: 60000});
    },
});

core.serviceRegistry.add('support_bus_service', SupportBusService);

return SupportBusService;

});

