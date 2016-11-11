odoo.define('web.Model', function (require) {
"use strict";

var Class = require('web.Class');
var session = require('web.session');

var Model = Class.extend({
    /**
    new openerp.web.Model(name[, context[, domain]])

    @constructs instance.web.Model
    @extends instance.web.Class

    @param {String} name name of the OpenERP model this object is bound to
    @param {Object} [context]
    @param {Array} [domain]
    */
    init: function(name, context, domain) {
        this.name = name;
        this._context = context || {};
        this._domain = domain || [];
    },
    /**
     * @deprecated does not allow to specify kwargs, directly use call() instead
     */
    get_func: function (method_name) {
        var self = this;
        return function () {
            return self.call(method_name, _.toArray(arguments));
        };
    },
    /**
     * Call a method (over RPC) on the bound OpenERP model.
     *
     * @param {String} method name of the method to call
     * @param {Array} [args] positional arguments
     * @param {Object} [kwargs] keyword arguments
     * @param {Object} [options] additional options for the rpc() method
     * @returns {jQuery.Deferred<>} call result
     */
    call: function (method, args, kwargs, options) {
        args = args || [];
        kwargs = kwargs || {};
        if (!_.isArray(args)) {
            // call(method, kwargs)
            kwargs = args;
            args = [];
        }
        var call_kw = '/web/dataset/call_kw/' + this.name + '/' + method;
        return session.rpc(call_kw, {
            model: this.name,
            method: method,
            args: args,
            kwargs: kwargs
        }, options);
    },
    /**
     * Executes a signal on the designated workflow, on the bound OpenERP model
     *
     * @param {Number} id workflow identifier
     * @param {String} signal signal to trigger on the workflow
     */
    exec_workflow: function (id, signal) {
        return session.rpc('/web/dataset/exec_workflow', {
            model: this.name,
            id: id,
            signal: signal
        });
    },
});

return Model;
});
