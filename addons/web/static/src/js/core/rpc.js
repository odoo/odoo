odoo.define('web.rpc', function (require) {
"use strict";

var ajax = require('web.ajax');

return {
    /**
     * Perform a RPC.  Please note that this is not the preferred way to do a
     * rpc if you are in the context of a widget.  In that case, you should use
     * the this._rpc method.
     *
     * @param {Object} params @see buildQuery for a description
     * @param {Object} options
     * @returns {Deferred<any>}
     */
    query: function (params, options) {
        var query = this.buildQuery(params);
        return ajax.rpc(query.route, query.params, options);
    },
    /**
     * @param {Object} options
     * @param {any[]} [options.args]
     * @param {Object} [options.context]
     * @param {any[]} [options.domain]
     * @param {string[]} [options.fields]
     * @param {string[]} [options.groupBy]
     * @param {Object} [options.kwargs]
     * @param {integer|false} [options.limit]
     * @param {string} [options.method]
     * @param {string} [options.model]
     * @param {integer} [options.offset]
     * @param {string[]} [options.orderBy]
     * @param {Object} [options.params]
     * @param {string} [options.route]
     * @returns {Object} with 2 keys: route and params
     */
    buildQuery: function (options) {
        var route;
        var params = options.params || {};
        if (options.route) {
            route = options.route;
        } else if (options.model && options.method) {
            route = '/web/dataset/call_kw/' + options.model + '/' + options.method;
        }
        if (options.method) {
            params.args = options.args || [];
            params.model = options.model;
            params.method = options.method;
            params.kwargs = options.kwargs || {};
            params.kwargs.context = options.context || params.kwargs.context;
        }

        if (options.method === 'read_group') {
            params.kwargs.groupby = options.groupBy || params.kwargs.groupby || [];
            params.kwargs.domain = options.domain || params.kwargs.domain || [];
            params.kwargs.fields = options.fields || params.kwargs.fields || [];
            params.kwargs.lazy = 'lazy' in options ? options.lazy : params.kwargs.lazy;
            var orderBy = options.orderBy || params.orderBy;
            params.kwargs.orderby = orderBy ? this._serializeSort(orderBy) : false;
        }

        if (options.method === 'search_read') {
            // call the model method
            params.args = [
                options.domain || [],
                options.fields || false,
                options.offset || 0,
                options.limit || false,
                this._serializeSort(options.orderBy || params.orderBy || []),
            ];
        }

        if (options.route === '/web/dataset/search_read') {
            // specifically call the controller
            params.model = options.model || params.model;
            params.domain = options.domain || params.domain || [];
            params.fields = options.fields || params.fields  || false;
            params.limit = options.limit || params.limit;
            params.offset = options.offset || params.offset ;
            params.sort = this._serializeSort(options.orderBy || params.orderBy || []);
            params.context = options.context || params.context || {};
        }

        return {
            route: route,
            params: JSON.parse(JSON.stringify(params)),
        };
    },
    /**
     * Helper method, generates a string to describe a ordered by sequence for
     * SQL.
     *
     * For example, [{name: 'foo'}, {name: 'bar', asc: false}] will
     * be converted into 'foo ASC, bar DESC'
     *
     * @param {Object[]} orderBy list of objects {name:..., [asc: ...]}
     * @returns {string}
     */
    _serializeSort: function (orderBy) {
        return _.map(orderBy, function (order) {
            return order.name + (order.asc !== false ? ' ASC' : ' DESC');
        }).join(', ');
    },
};

});
