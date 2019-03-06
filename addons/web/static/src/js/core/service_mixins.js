odoo.define('web.ServiceProviderMixin', function (require) {
"use strict";

var core = require('web.core');

var ServiceProviderMixin = {
    services: {}, // dict containing deployed service instances
    UndeployedServices: {}, // dict containing classes of undeployed services
    /**
     * @override
     */
    init: function (parent) {
        var self = this;
        // to properly instantiate services with this as parent, this mixin
        // assumes that it is used along the EventDispatcherMixin, and that
        // EventDispatchedMixin's init is called first
        // as EventDispatcherMixin's init is already called, this handler has
        // to be bound manually
        this.on('call_service', this, this._call_service.bind(this));

        // add already registered services from the service registry
        _.each(core.serviceRegistry.map, function (Service, serviceName) {
            if (serviceName in self.UndeployedServices) {
                throw new Error('Service "' + serviceName + '" is already loaded.');
            }
            self.UndeployedServices[serviceName] = Service;
        });
        this._deployServices();

        // listen on newly added services
        core.serviceRegistry.onAdd(function (serviceName, Service) {
            if (serviceName in self.services || serviceName in self.UndeployedServices) {
                throw new Error('Service "' + serviceName + '" is already loaded.');
            }
            self.UndeployedServices[serviceName] = Service;
            self._deployServices();
        });
    },

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

var rpc = require('web.rpc');

/**
 * @mixin
 * @name ServicesMixin
 */
var ServicesMixin = {
    /**
     * @param  {string} service
     * @param  {string} method
     * @return {any} result of the service called
     */
    call: function (service, method) {
        var args = Array.prototype.slice.call(arguments, 2);
        var result;
        this.trigger_up('call_service', {
            service: service,
            method: method,
            args: args,
            callback: function (r) {
                result = r;
            },
        });
        return result;
    },
    /**
     * Builds and executes RPC query. Returns a deferred's promise resolved with
     * the RPC result.
     *
     * @param {string} params either a route or a model
     * @param {string} options if a model is given, this argument is a method
     * @returns {Promise}
     */
    _rpc: function (params, options) {
        var query = rpc.buildQuery(params);
        var def = this.call('ajax', 'rpc', query.route, query.params, options, this) || $.Deferred();
        var promise = def.promise();
        var abort = (def.abort ? def.abort : def.reject) || function () {};
        promise.abort = abort.bind(def);
        return promise;
    },
    loadFieldView: function (dataset, view_id, view_type, options) {
        return this.loadViews(dataset.model, dataset.get_context().eval(), [[view_id, view_type]], options).then(function (result) {
            return result[view_type];
        });
    },
    loadViews: function (modelName, context, views, options) {
        var def = $.Deferred();
        this.trigger_up('load_views', {
            modelName: modelName,
            context: context,
            views: views,
            options: options,
            on_success: def.resolve.bind(def),
        });
        return def;
    },
    loadFilters: function (dataset, action_id) {
        var def = $.Deferred();
        this.trigger_up('load_filters', {
            dataset: dataset,
            action_id: action_id,
            on_success: def.resolve.bind(def),
        });
        return def;
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
     * deferred.
     *
     * @param {any} action
     * @param {any} options
     * @returns {Deferred}
     */
    do_action: function (action, options) {
        var def = $.Deferred();

        this.trigger_up('do_action', {
            action: action,
            options: options,
            on_success: function (result) { def.resolve(result); },
            on_fail: function (result) { def.reject(result); },
        });
        return def;
    },
    do_notify: function (title, message, sticky, className) {
        return this.call('notification', 'notify', {title: title, message: message, sticky: sticky, className: className});
    },
    do_warn: function (title, message, sticky, className) {
        return this.call('notification', 'notify', {type: 'warning', title: title, message: message, sticky: sticky, className: className});
    },
};

return ServicesMixin;

});
