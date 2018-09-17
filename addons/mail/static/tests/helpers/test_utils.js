odoo.define('mail.testUtils', function (require) {
"use strict";

var BusService = require('bus.BusService');

var Discuss = require('mail.Discuss');
var MailService = require('mail.Service');

var AbstractStorageService = require('web.AbstractStorageService');
var Class = require('web.Class');
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
 * This is async due to mail_manager/mail_service that needs to be ready.
 *
 * @param {Object} params
 * @return {$.Promise} resolved with the discuss widget
 */
function createDiscuss(params) {
    var Parent = Widget.extend({
        do_push_state: function () {},
    });
    var parent = new Parent();
    params.archs = params.archs || {
        'mail.message,false,search': '<search/>',
    };
    testUtils.addMockEnvironment(parent, params);
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


var MockMailService = Class.extend({
    bus_service: function () {
        return BusService.extend({
            _poll: function () {}, // Do nothing
            isOdooFocused: function () { return true; },
            updateOption: function () {},
        });
    },
    mail_service: function () {
        return MailService;
    },
    local_storage: function () {
        return AbstractStorageService.extend({
            storage: new RamStorage(),
        });
    },
    getServices: function () {
        return {
            mail_service: this.mail_service(),
            bus_service: this.bus_service(),
            local_storage: this.local_storage(),
        };
    },
});

/**
 * Returns the list of mail services required by the mail components: a
 * mail_service, and its two dependencies bus_service and local_storage.
 *
 * @return {AbstractService[]} an array of 3 services: mail_service, bus_service
 * and local_storage, in that order
 */
function getMailServices() {
    return new MockMailService().getServices();
}

return {
    MockMailService: MockMailService,
    createDiscuss: createDiscuss,
    getMailServices: getMailServices,
};

});
