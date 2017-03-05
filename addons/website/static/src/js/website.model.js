/**
 * Service to fetch data, websites Javascript must use performModelRPC of this module
 */
odoo.define('website.model', function (require) {
"use strict";

var Class = require('web.Class');
var Mixins = require('web.mixins');
var ajax = require('web.ajax');

var CallService = Class.extend(Mixins.EventDispatcherMixin, {
    custom_events: {
        call_service: '_callService'
    },
    init: function () {
        Mixins.EventDispatcherMixin.init.call(this);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     */
    _callService: function (event) {
        var result = ajax[event.data.method].apply(ajax, event.data.args);
        event.data.callback(result);
    },
});

var Model =  Class.extend(Mixins.EventDispatcherMixin, Mixins.ServicesMixin, {
    init: function (parent) {
        Mixins.EventDispatcherMixin.init.call(this);
        this.setParent(parent);
    },
});

return new Model(new CallService());
});
