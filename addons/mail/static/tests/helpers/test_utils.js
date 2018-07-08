odoo.define('mail.testUtils', function (require) {
"use strict";

var Discuss = require('mail.Discuss');
var MailService = require('mail.Service');

var AbstractService = require('web.AbstractService');
var AbstractStorageService = require('web.AbstractStorageService');
var Bus = require('web.Bus');
var ControlPanel = require('web.ControlPanel');
var RamStorage = require('web.RamStorage');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

/**
 * Test Utils
 *
 * In this module, we define some utility functions to create mock objects
 * in the mail module, such as the BusService or Discuss.
 */

/**
 * Create asynchronously a discuss widget.
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

    return  discuss.appendTo($(selector)).then(function () {
        return discuss;
    });
}

/**
 * Returns the list of mail services required by the mail components: a
 * mail_service, and its two dependencies bus_service and local_storage.
 *
 * @return {AbstractService[]} an array of 3 services: mail_service, bus_service
 * and local_storage, in that order
 */
function getMailServices() {
    var MockBus = Bus.extend({
        /**
         * Do nothing
         */
        start_polling: function () {},
        is_odoo_focused: function () { return true; },
    });
    var BusService =  AbstractService.extend({
        name: 'bus_service',
        bus: new MockBus(),

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * @returns {Bus}
         */
        getBus: function () {
            return this.bus;
        }
    });
    var LocalStorageService = AbstractStorageService.extend({
        name: 'local_storage',
        storage: new RamStorage(),
    });
    return [MailService, BusService, LocalStorageService];
}

return {
    createDiscuss: createDiscuss,
    getMailServices: getMailServices,
};

});
