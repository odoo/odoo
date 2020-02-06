odoo.define('mail.testUtils', function (require) {
"use strict";

var BusService = require('bus.BusService');

var Discuss = require('mail.Discuss');
const MessagingService = require('mail.messaging.service.Messaging');
var MailService = require('mail.Service');

var AbstractStorageService = require('web.AbstractStorageService');
var Class = require('web.Class');
const dom = require('web.dom');
var RamStorage = require('web.RamStorage');
const makeTestEnvironment = require('web.test_env');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

const { prepareTarget } = testUtils;
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
 * @returns {Promise<Discuss>}
 */
async function createDiscuss(params) {
    const target = prepareTarget(params.debug);
    const Parent = Widget.extend({
        do_push_state: function () {},
    });
    const parent = new Parent();
    params.archs = params.archs || {
        'mail.message,false,search': '<search/>',
    };
    await testUtils.mock.addMockEnvironment(parent, params);

    const env = params.env || {};
    owl.Component.env = makeTestEnvironment(env);

    const discuss = new Discuss(parent, params);

    // override 'destroy' of discuss so that it calls 'destroy' on the parent
    // instead, which is the parent of discuss and the mockServer.
    const _destroy = discuss.destroy;
    discuss.destroy = function () {
        // remove the override to properly destroy discuss and its children
        // when it will be called the second time (by its parent)
        discuss.destroy = _destroy;
        discuss.on_detach_callback();
        parent.destroy();
    };

    const fragment = document.createDocumentFragment();
    await discuss.appendTo(fragment);
    dom.prepend(target, fragment, {
        callbacks: [{ widget: discuss }],
        in_DOM: true,
    });
    return discuss;
}


var MockMailService = Class.extend({
    bus_service: function () {
        return BusService.extend({
            _poll: function () {}, // Do nothing
            _registerWindowUnload: function () {}, // Do nothing
            isOdooFocused: function () { return true; },
            updateOption: function () {},
        });
    },
    mail_service: function () {
        return MailService;
    },
    messaging() {
        return MessagingService;
    },
    local_storage: function () {
        return AbstractStorageService.extend({
            storage: new RamStorage(),
        });
    },
    getServices: function () {
        return {
            mail_service: this.mail_service(),
            messaging: this.messaging(),
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
