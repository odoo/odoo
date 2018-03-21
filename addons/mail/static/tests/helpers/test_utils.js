odoo.define('mail.testUtils', function (require) {
"use strict";

var Discuss = require('mail.chat_discuss');

var AbstractService = require('web.AbstractService');
var Bus = require('web.Bus');
var ControlPanel = require('web.ControlPanel');
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
        init: function () {
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

/**
 * Create asynchronously a discuss widget.
 * This is async due to chat_manager service that needs to be ready.
 *
 * @param {Object} params
 * @return {$.Promise} resolved with the discuss widget
 */
function createDiscuss(params) {
    var Parent = Widget.extend({
        do_push_state: function () {},
    });
    var parent = new Parent();
    testUtils.addMockEnvironment(parent, _.extend(params, {
        archs: {
            'mail.message,false,search': '<search/>',
        },
    }));
    var discuss = new Discuss(parent, params);
    discuss.set_cp_bus(new Widget());
    var selector = params.debug ? 'body' : '#qunit-fixture';
    var controlPanel = new ControlPanel(parent);
    controlPanel.appendTo($(selector));
    discuss.appendTo($(selector));

    // override 'destroy' of discuss so that it calls 'destroy' on the parent
    // instead, which is the parent of discuss and the mockServer.
    discuss.destroy = function () {
        // remove the override to properly destroy discuss and its children
        // when it will be called the second time (by its parent)
        delete discuss.destroy;
        parent.destroy();
    };

    // link the view to the control panel
    discuss.set_cp_bus(controlPanel.get_bus());

    return discuss.call('chat_manager', 'isReady').then(function () {
        return discuss;
    });
}

return {
    createBusService: createBusService,
    createDiscuss: createDiscuss,
};

});
