odoo.define('web.ServiceProviderMixin', function (require) {
"use strict";

var AbstractService = require('web.AbstractService');
var utils = require('web.utils');

var ServiceProviderMixin = {
    services: {},
    init: function () {
        // to properly instantiate services with this as parent, this mixin
        // assumes that it is used along the EventDispatcherMixin, and that
        // EventDispatchedMixin's init is called first
        var self = this;
        // as EventDispatcherMixin's init is already called, this handler has to
        // be bound manually
        this.on('call_service', this, this._call_service.bind(this));

        var sortedServices = this._sortServices(AbstractService.prototype.Services);
        _.each(sortedServices, function (Service) {
            var service = new Service(self);
            self.services[service.name] = service;
        });
    },
    _call_service: function (event) {
        var service = this.services[event.data.service];
        var args = event.data.args || [];
        // ajax service uses an extra 'target' argument for rpc
        if (event.data.service === 'ajax' && event.data.method === 'rpc') {
            args = args.concat(event.target);
        }
        var result = service[event.data.method].apply(service, args);
        event.data.callback(result);
    },
    _sortServices: function (services) {
        var nodes = {};
        // Create nodes (services)
        _.each(services, function (Service) {
            nodes[Service.prototype.name] = Service.prototype.dependencies;
        });
        var sorted;
        try {
            sorted = utils.topologicalSort(nodes);
        } catch (err) {
            console.warn('topologicalSort Error:', err.message);
            sorted = nodes;
        }
        // Sort services based on sorted
        // Note: we convert sorted to an object key=>index for efficiency
        var sortedObj = _.invert(_.object(_.pairs(sorted)));
        sorted = _.sortBy(services, function (Service) {
            return sortedObj[Service.prototype.name];
        });

        return sorted;
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
        var def = this.call('ajax', 'rpc', query.route, query.params, options);
        return def ? def.promise() : $.Deferred().promise();
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
        this.trigger_up('notification', {title: title, message: message, sticky: sticky, className: className});
    },
    do_warn: function (title, message, sticky, className) {
        this.trigger_up('warning', {title: title, message: message, sticky: sticky, className: className});
    },
};

return ServicesMixin;

});
