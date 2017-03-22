odoo.define('web.rpc', function (require) {
"use strict";

var ajax = require('web.ajax');
var Class = require('web.Class');

var BaseRPCBuilder = Class.extend({
    /**
     * @param {Widget} parent the rpc will go through this widget
     * @param {Object} params
     * @param {string} [params.model]
     * @param {string} [params.method]
     * @param {string} [params.route]
     */
    init: function (parent, params) {
        this.parent = parent;
        this._route = params.route;
        if (!this._route) {
            this._route = '/web/dataset/call_kw/' + params.model + '/' + params.method;
        }
        this._model = params.model;
        this._method = params.method;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Array} args
     * @returns {BaseRPCBuilder}
     */
    args: function (args) {
        if (!(args instanceof Array)) {
            throw new Error("Arguments should be an array");
        }
        this._args = args;
        return this;
    },
    /**
     * @param {Object} [params]
     * @param {string} [params.type=event] if type=event, the rpc will be done
     *   by triggering an event.  It will work if the parent is in a component
     *   tree with a component with a ServiceProvider somewhere up.  If
     *   type=ajax, then it will instead perform directly an ajax call.  This is
     *   discouraged, if possible.
     * @param {Object} [params.options] options that will be sent to the low
     *   level ajax call.  Typically, shadow=true.
     * @return {Deferred<*>}
     */
    exec: function (params) {
        var route = this._getRoute();
        var options = (params && params.options) ? params.options : {};
        var type = (params && params.type) ? params.type : 'event';

        if (type === 'event') {
            return this.parent.call('ajax', 'rpc', route, this._getParams(), options);
        } else if (type === 'ajax') {
            return ajax.rpc(route, this._getParams(), options);
        }
    },
    /**
     * @param {Object} kwargs
     * @returns {BaseRPCBuilder}
     */
    kwargs: function (kwargs) {
        this._kwargs = kwargs;
        return this;
    },
    /**
     * @param {Object} params
     * @returns {BaseRPCBuilder}
     */
    params: function (params) {
        this._params = params;
        return this;
    },
    /**
     * @param {Object} context
     * @returns {BaseRPCBuilder}
     */
    withContext: function (context) {
        this._context = context;
        return this;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Object}
     */
    _getParams: function () {
        var kwargs = _.extend({}, this._kwargs);
        if (this._context) {
            kwargs.context = this._context;
        }
        var params = {
            method: this._method,
            model: this._model,
            args: this._args || (this._method ? [] : undefined),
            kwargs: this._method ? kwargs : undefined,
        };
        return _.defaults(params, this._params);
    },
    /**
     * @private
     * @returns {string}
     */
    _getRoute: function () {
        return this._route;
    },
});

var SearchRPCBuilder = BaseRPCBuilder.extend({
    init: function () {
        this._super.apply(this, arguments);
        this._route = '/web/dataset/search_read';
        this._orderBy = false;
        this._domain = [];
        this._fields = false;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Object[]} orderBy
     * @returns {BaseRPCBuilder}
     */
    orderBy: function (orderBy) {
        // todo: serialize properly this
        this._orderBy = this._serializeSort(orderBy);
        return this;
    },
    /**
     * @param {Object} context
     * @returns {BaseRPCBuilder}
     */
    withContext: function (context) {
        this._context = context;
        return this;
    },
    /**
     * @param {Object} domain
     * @returns {BaseRPCBuilder}
     */
    withDomain: function (domain) {
        this._domain = domain;
        return this;
    },
    /**
     * @param {string[]} fields
     * @returns {BaseRPCBuilder}
     */
    withFields: function (fields) {
        this._fields = fields;
        return this;
    },
    /**
     * @param {Object} limit
     * @returns {BaseRPCBuilder}
     */
    withLimit: function (limit) {
        this._limit = limit;
        return this;
    },
    /**
     * @param {Object} offset
     * @returns {BaseRPCBuilder}
     */
    withOffset: function (offset) {
        this._offset = offset;
        return this;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @returns {Object}
     */
    _getParams: function () {
        return {
            context: this._context || {},
            domain: this._domain,
            fields: this._fields,
            limit: this._limit,
            model: this._model,
            offset: this._offset,
            sort: this._orderBy
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
});

var ReadGroupRPCBuilder = SearchRPCBuilder.extend({
    init: function () {
        this._super.apply(this, arguments);
        this._route = '/web/dataset/call_kw/' + this._model + '/read_group';
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * We need to make sure that arguments are properly set.
     * @override
     * @returns {Deferred<*>}
     */
    exec: function () {
        if (!this._groupBy) {
            throw new Error("read_group must have a group_by argument");
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @param {string[]} groupBy
     * @returns {BaseRPCBuilder}
     */
    groupBy: function (groupBy) {
        // todo: serialize properly this
        this._groupBy = groupBy;
        return this;
    },
    /**
     * @param {boolean} lazy
     * @returns {BaseRPCBuilder}
     */
    lazy: function (lazy) {
        // todo: serialize properly this
        this._lazy = lazy;
        return this;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @returns {Object}
     */
    _getParams: function () {
        var kwargs = _.defaults({}, this._kwargs, {
            context: this._context || {},
            domain: this._domain || [],
            fields: this._fields,
            groupby: this._groupBy,
            lazy: !!this._lazy,
            orderby: this._orderBy,
        });
        return {
            args: this._args || [],
            kwargs: kwargs,
            method: 'read_group',
            model: this._model,
        };
    },
});

return {
    builders: {
        default: BaseRPCBuilder,
        search_read: SearchRPCBuilder,
        read_group: ReadGroupRPCBuilder,
    },
    query: function (params) {
        var Builder = this.builders[params.method] || this.builders.default;
        return new Builder(params.parent, params);
    },
};

});
