odoo.define('mail.testUtils', function (require) {
"use strict";

var BusService = require('bus.BusService');

var Discuss = require('mail.Discuss');
var MailService = require('mail.Service');
var mailUtils = require('mail.utils');

var AbstractStorageService = require('web.AbstractStorageService');
var Class = require('web.Class');
var ControlPanelView = require('web.ControlPanelView');
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
 * @return {Promise} resolved with the discuss widget
 */
async function createDiscuss(params) {
    var Parent = Widget.extend({
        do_push_state: function () {},
    });
    var parent = new Parent();
    params.archs = params.archs || {
        'mail.message,false,search': '<search/>',
    };
    testUtils.mock.addMockEnvironment(parent, params);
    var discuss = new Discuss(parent, params);
    var selector = params.debug ? 'body' : '#qunit-fixture';

    // override 'destroy' of discuss so that it calls 'destroy' on the parent
    // instead, which is the parent of discuss and the mockServer.
    discuss.destroy = function () {
        // remove the override to properly destroy discuss and its children
        // when it will be called the second time (by its parent)
        delete discuss.destroy;
        parent.destroy();
    };

    return discuss.appendTo($(selector)).then(function () {
        return discuss;
    });
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
 * Patch all the mailUtils.clearTimeout and mailUtils.setTimeout.
 *
 * @return {Object} helper functions, including unpatch and time management tools.
 */
var patchMailTimeouts = function () {
    var currentTime = 0;
    var timeouts = {};
    var countTimeout = 0;

    mailUtils.clearTimeout = function (id) {
        delete timeouts[id];
    };

    mailUtils.setTimeout = function (func, duration) {
        duration = duration || 0;
        var executeTime = currentTime + duration;
        countTimeout++;
        timeouts[countTimeout] = {
            executeTime: executeTime,
            func: func
        };
        return countTimeout;
    };
    /**
     * @return {integer|boolean} id of the next timeout in queue, false if queue is empty
     */
    function getNextTimeoutId() {
        var minKey = false;
        _.each(timeouts, function (value, key) {
            if (minKey === false) {
                minKey = Number(key);
                return;
            }
            var minTime = timeouts[minKey].executeTime;
            if (value.executeTime < minTime || (value.executeTime === minTime && key < minKey)) {
                minKey = Number(key);
            }
        });
        return minKey;
    }

    /**
     * @return {integer|boolean} delay (time interval) before the next timeout in queue is executed.
     *   Useful to know how much time to advance to execute next timer.
     */
    function getNextTimeoutDelay() {
        var next = getNextTimeoutId();
        if (next === false) {
            return false;
        }
        return timeouts[next].executeTime - currentTime;
    }

    /**
     * Set the current time to given time
     *
     * @param {integer} time
     */
    function setTime(time) {
        var next = getNextTimeoutId();
        if (next !== false && timeouts[next].executeTime <= time) {
            currentTime = timeouts[next].executeTime;
            var func = timeouts[next].func;
            // watch out setTimeout inside setTimeout (recursive)
            delete timeouts[next];
            func();
            setTime(time);
        }
        else {
            currentTime = time;
        }
    }

    /**
     * Add the given time to current time
     *
     * @param {integer} time
     */
    function addTime(time) {
        setTime(currentTime + time);
    }

    /**
     * Set time to the max time in queue and execute all timeouts before this time.
     */
    function runPendingTimeouts() {
        var maxTimeInQueue = 0;
        _.each(timeouts, function (value, key) {
            if (value.executeTime > maxTimeInQueue) {
                maxTimeInQueue = value.executeTime;
            }
        });
        setTime(maxTimeInQueue);
    }

    return {
        addTime: addTime,
        getNextTimeoutDelay:getNextTimeoutDelay,
        runPendingTimeouts: runPendingTimeouts,
        setTime: setTime,
    };
};


/**
 * Returns the list of mail services required by the mail components: a
 * mail_service, and its two dependencies bus_service and local_storage.
 *
 * @return {AbstractService[]} an array of 3 services: mail_service, bus_service
 * and local_storage, in that order
 */
function getMailServices() {
    patchMailTimeouts();
    return new MockMailService().getServices();
}

return {
    MockMailService: MockMailService,
    createDiscuss: createDiscuss,
    getMailServices: getMailServices,
    patchMailTimeouts: patchMailTimeouts,
};

});
