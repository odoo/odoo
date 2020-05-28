odoo.define('web.AbstractService', function (require) {
"use strict";

var Class = require('web.Class');
var Mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');

var AbstractService = Class.extend(Mixins.EventDispatcherMixin, ServicesMixin, {
    dependencies: [],
    init: function (env) {
        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.env = env;
    },
    /**
     * @abstract
     */
    start: function () {},
    /**
     * Directly calls the requested service, instead of triggering a
     * 'call_service' event up, which wouldn't work as services have no parent
     *
     * @param {OdooEvent} ev
     */
    _trigger_up: function (ev) {
        Mixins.EventDispatcherMixin._trigger_up.apply(this, arguments);
        if (ev.is_stopped()) {
            return;
        }
        const payload = ev.data;
        if (ev.name === 'call_service') {
            let args = payload.args || [];
            if (payload.service === 'ajax' && payload.method === 'rpc') {
                // ajax service uses an extra 'target' argument for rpc
                args = args.concat(ev.target);
            }
            const service = this.env.services[payload.service];
            const result = service[payload.method].apply(service, args);
            payload.callback(result);
        } else if (ev.name === 'do_action') {
            this.env.bus.trigger('do-action', payload);
        }
    },
});

return AbstractService;
});
