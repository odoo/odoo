/** @odoo-module alias=web.ServicesMixin **/

import rpc from "web.rpc";

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
     * Builds and executes RPC query. Returns a promise resolved with
     * the RPC result.
     *
     * @param {string} params either a route or a model
     * @param {string} options if a model is given, this argument is a method
     * @returns {Promise}
     */
    _rpc: function (params, options) {
        var query = rpc.buildQuery(params);
        var prom = this.call('ajax', 'rpc', query.route, query.params, options, this);
        if (!prom) {
            prom = new Promise(function () {});
            prom.abort = function () {};
        }
        var abort = prom.abort ? prom.abort : prom.reject;
        if (abort) {
            prom.abort = abort.bind(prom);
        }
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
                on_fail: (reason) => {
                    reject(reason);
                    return "alreadyThrown"
                },
            });
        });
    },
    /**
     * Displays a notification.
     *
     * @param {Object} options
     * @param {string} [options.title]
     * @param {string} [options.subtitle]
     * @param {string} [options.message]
     * @param {string} [options.type='warning'] 'info', 'success', 'warning', 'danger' or ''
     * @param {boolean} [options.sticky=false]
     * @param {string} [options.className]
     */
    displayNotification: function (options) {
        return this.call('notification', 'notify', options);
    },
};

export default ServicesMixin;
