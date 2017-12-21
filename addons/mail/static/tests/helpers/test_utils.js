odoo.define('mail.testUtils', function (require) {
"use strict";

var Discuss = require('mail.chat_discuss');

var AbstractService = require('web.AbstractService');
var Bus = require('web.Bus');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

/**
 * Test Utils
 *
 * In this module, we define some utility functions to create mock objects
 * in the mail module, such as the BusService or Discuss.
 */

/**
 * Create a mock bus_service, using 'bus' instead of bus.bus
 * 
 * @param {web.bus} bus
 * @return {AbstractService} the mock bus_service
 */
function createBusService(bus) {

    var BusService =  AbstractService.extend({
        name: 'bus_service',
        /**
         * @override
         */
        init: function (parent) {
            this._super.apply(this, arguments);
            if (!bus) {
                bus = new Bus();
            }
            this.bus = new _.extend(bus, {
                /**
                 * Do nothing 
                 */
                start_polling: function () {},
            });
        },
    
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
    
        /**
         * Get the bus
         */
        getBus: function () {
            return this.bus;
        },
    
    });
    
    return BusService;
}

function createDiscuss(params) {
    var Parent = Widget.extend({
        do_push_state: function () {},
    });
    var parent = new Parent();
    testUtils.addMockEnvironment(parent, {
        data: params.data,
        archs: {
            'mail.message,false,search': '<search/>',
        },
        mockRPC: params.mockRPC,
        services: params.services,
    });
    var discuss = new Discuss(parent, params);
    discuss.set_cp_bus(new Widget());
    discuss.appendTo($('#qunit-fixture'));

    return discuss;
}

return {
    createBusService: createBusService,
    createDiscuss: createDiscuss,
};

});
