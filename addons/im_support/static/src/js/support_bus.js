odoo.define('im_support.SupportBus', function (require) {
"use strict";

/**
 * This module instantiates and exports the instance of the Bus, parameterized
 * to poll the Support server.
 */

var supportSession = require('im_support.SupportSession');

var bus = require('bus.bus');

var Bus;
if(typeof Storage !== "undefined"){
    Bus = bus.CrossTabBus;
} else {
    Bus = bus.Bus;
}

var params = {
    session: supportSession,
    pollRoute: '/longpolling/support_poll',
};

return new Bus(params);

});

