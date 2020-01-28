odoo.define('web.ServiceProviderMixin', function (require) {
"use strict";

var ServiceProviderMixin = {
    services: {}, // dict containing deployed service instances
    UndeployedServices: {}, // dict containing classes of undeployed services
    /**
     * @override
     */
    init: function (parent) {},

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _deployServices: function () {
        var self = this;
        var done = false;
        while (!done) {
            var serviceName = _.findKey(this.UndeployedServices, function (Service) {
                // no missing dependency
                return !_.some(Service.prototype.dependencies, function (depName) {
                    return !self.services[depName];
                });
            });
            if (serviceName) {
                var service = new this.UndeployedServices[serviceName](this);
                this.services[serviceName] = service;
                delete this.UndeployedServices[serviceName];
                service.start();
            } else {
                done = true;
            }
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Call the 'service', using data from the 'event' that
     * has triggered the service call.
     *
     * For the ajax service, the arguments are extended with
     * the target so that it can call back the caller.
     *
     * @private
     * @param  {OdooEvent} event
     */
    _call_service: function (event) {
        var args = event.data.args || [];
        if (event.data.service === 'ajax' && event.data.method === 'rpc') {
            // ajax service uses an extra 'target' argument for rpc
            args = args.concat(event.target);
        }
        var service = this.services[event.data.service];
        var result = service[event.data.method].apply(service, args);
        event.data.callback(result);
    },
};

return ServiceProviderMixin;

});

odoo.define('web.ServicesMixin', function (require) {
"use strict";

const env = require('web.env');
var rpc = require('web.rpc');

/**
 * @mixin
 * @name ServicesMixin
 */
var ServicesMixin = {
    env,
    /**
     * @param {string} serviceName
     * @param {string} methodName
     * @param {...any} args
     * @return {any} result of the service called
     */
    call(serviceName, methodName, ...args) {
        if (serviceName === 'ajax' && methodName === 'rpc') {
            // ajax service uses an extra 'target' argument for rpc
            args = args.concat(this);
        }
        const service = this.env.services[serviceName];
        return service[methodName].apply(service, args);
    },
    /**
     * Builds and executes RPC query. Returns a promise resolved with
     * the RPC result.
     *
     * @param {string} params either a route or a model
     * @param {string} options if a model is given, this argument is a method
     * @returns {Promise}
     */
    _rpc: function (params, options) {
        var query = rpc.buildQuery(params);
        var prom = this.env.services.ajax.rpc(query.route, query.params, options, this);
        if (!prom) {
            prom = new Promise(function () {});
            prom.abort = function () {};
        }
        var abort = prom.abort ? prom.abort : prom.reject;
        if (!abort) {
            throw new Error("a rpc promise should always have a reject function");
        }
        prom.abort = abort.bind(prom);
        return prom;
    },
    loadFieldView: function (modelName, context, view_id, view_type, options) {
        return this.loadViews(modelName, context, [[view_id, view_type]], options).then(function (result) {
            return result[view_type];
        });
    },
    loadViews: function (modelName, context, views, options) {
        var self = this;
        return new Promise(function (resolve) {
            self.trigger_up('load_views', {
                modelName: modelName,
                context: context,
                views: views,
                options: options,
                on_success: resolve,
            });
        });
    },
    loadFilters: function (modelName, actionId, context) {
        var self = this;
        return new Promise(function (resolve, reject) {
            self.trigger_up('load_filters', {
                modelName: modelName,
                actionId: actionId,
                context: context,
                on_success: resolve,
            });
        });
    },
    createFilter: function (filter) {
        var self = this;
        return new Promise(function (resolve, reject) {
            self.trigger_up('create_filter', {
                filter: filter,
                on_success: resolve,
            });
        });
    },
    deleteFilter: function (filterId) {
        var self = this;
        return new Promise(function (resolve, reject) {
            self.trigger_up('delete_filter', {
                filterId: filterId,
                on_success: resolve,
            });
        });
    },
    // Session stuff
    getSession: function () {
        var session;
        this.trigger_up('get_session', {
            callback: function (result) {
                session = result;
            }
        });
        return session;
    },
    /**
     * Informs the action manager to do an action. This supposes that the action
     * manager can be found amongst the ancestors of the current widget.
     * If that's not the case this method will simply return an unresolved
     * promise.
     *
     * @param {any} action
     * @param {any} options
     * @returns {Promise}
     */
    do_action: function (action, options) {
        var self = this;
        return new Promise(function (resolve, reject) {
            self.trigger_up('do_action', {
                action: action,
                options: options,
                on_success: resolve,
                on_fail: reject,
            });
        });
    },
    /**
     * Displays a notification.
     *
     * @param {Object} options
     * @param {string} options.title
     * @param {string} [options.subtitle]
     * @param {string} [options.message]
     * @param {string} [options.type='warning'] 'info', 'success', 'warning', 'danger' or ''
     * @param {boolean} [options.sticky=false]
     * @param {string} [options.className]
     */
    displayNotification: function (options) {
        return this.env.services.notification.notify(options);
    },
    /**
     * @deprecated will be removed as soon as the notification system is reviewed
     * @see displayNotification
     */
    do_notify: function (title, message, sticky, className) {
        return this.displayNotification({
            type: 'warning',
            title: title,
            message: message,
            sticky: sticky,
            className: className,
        });
    },
    /**
     * @deprecated will be removed as soon as the notification system is reviewed
     * @see displayNotification
     */
    do_warn: function (title, message, sticky, className) {
        console.warn(title, message);
        return this.displayNotification({
            type: 'danger',
            title: title,
            message: message,
            sticky: sticky,
            className: className,
        });
    },
};

return ServicesMixin;

});
