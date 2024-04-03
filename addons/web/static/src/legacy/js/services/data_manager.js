odoo.define('web.DataManager', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var rpc = require('web.rpc');
var session = require('web.session');
const { generateLegacyLoadViewsResult } = require("@web/legacy/legacy_load_views");

return core.Class.extend({
    init: function () {
        this._init_cache();
        core.bus.on('clear_cache', this, this.invalidate.bind(this));
    },

    _init_cache: function () {
        this._cache = {
            actions: {},
            filters: {},
            views: {},
        };
    },

    /**
     * Invalidates the whole cache. Only works when not triggered by itself.
     * Suggestion: could be refined to invalidate some part of the cache
     *
     * @param {Object} [dataManager]
     */
    invalidate: function (dataManager) {
        if (dataManager === this) {
            return;
        }
        session.invalidateCacheKey('load_menus');
        this._init_cache();
    },

    /**
     * Loads an action from its id or xmlid.
     *
     * @param {int|string} [action_id] the action id or xmlid
     * @param {Object} [additional_context] used to load the action
     * @return {Promise} resolved with the action whose id or xmlid is action_id
     */
    load_action: function (action_id, additional_context) {
        var self = this;
        var key = this._gen_key(action_id, additional_context || {});

        if (config.isDebug('assets') || !this._cache.actions[key]) {
            this._cache.actions[key] = rpc.query({
                route: "/web/action/load",
                params: {
                    action_id: action_id,
                    additional_context: additional_context,
                },
            }).then(function (action) {
                self._cache.actions[key] = action.no_cache ? null : self._cache.actions[key];
                return action;
            }).guardedCatch(() => this._invalidate('actions', key));
        }

        return this._cache.actions[key].then(function (action) {
            return $.extend(true, {}, action);
        });
    },

    /**
     * Loads various information concerning views: fields_view for each view,
     * the fields of the corresponding model, and optionally the filters.
     *
     * @param {Object} params
     * @param {String} params.model
     * @param {Object} params.context
     * @param {Array} params.views_descr array of [view_id, view_type]
     * @param {Object} [options={}] dictionary of various options:
     *     - options.load_filters: whether or not to load the filters,
     *     - options.action_id: the action_id (required to load filters),
     *     - options.toolbar: whether or not a toolbar will be displayed,
     * @return {Promise} resolved with the requested views information
     */
    load_views: async function ({ model, context, views_descr } , options = {}) {
        const viewsKey = this._gen_key(model, views_descr, options, context);
        const filtersKey = this._gen_key(model, options.action_id);
        const withFilters = Boolean(options.load_filters);
        const shouldLoadViews = config.isDebug('assets') || !this._cache.views[viewsKey];
        const shouldLoadFilters = config.isDebug('assets') || (
            withFilters && !this._cache.filters[filtersKey]
        );
        if (shouldLoadViews) {
            // Views info should be loaded
            options.load_filters = shouldLoadFilters;
            if (config.device.isMobile) {
                options.mobile = config.device.isMobile;
            }
            this._cache.views[viewsKey] = rpc.query({
                args: [],
                kwargs: { context, options, views: views_descr },
                model,
                method: 'get_views',
            }).then(result => {
                const { models, views } = result;
                result = generateLegacyLoadViewsResult(model, views, models);
                // Freeze the fields dict as it will be shared between views and
                // no one should edit it
                // utils.deepFreeze(result.fields); // OWL issue regarding proxies and frozen objects https://github.com/odoo/owl/issues/1158
                for (const [ /* viewId */ , viewType] of views_descr) {
                    const fvg = result.fields_views[viewType];
                    fvg.viewFields = fvg.fields;
                    fvg.fields = result.fields;
                }

                // Insert filters, if any, into the filters cache
                if (shouldLoadFilters) {
                    this._cache.filters[filtersKey] = Promise.resolve(result.filters);
                }
                return result.fields_views;
            }).guardedCatch(() => this._invalidate('views', viewsKey));
        }
        const result = await this._cache.views[viewsKey];
        if (withFilters && result.search) {
            if (shouldLoadFilters) {
                await this.load_filters({
                    actionId: options.action_id,
                    context,
                    forceReload: false,
                    modelName: model,
                });
            }
            result.search.favoriteFilters = await this._cache.filters[filtersKey];
        }
        return result;
    },

    /**
     * Loads the filters of a given model and optional action id.
     *
     * @param {Object} params
     * @param {number} params.actionId
     * @param {Object} params.context
     * @param {boolean} [params.forceReload=true] can be set to false to prevent forceReload
     * @param {string} params.modelName
     * @return {Promise} resolved with the requested filters
     */
    load_filters: function (params) {
        const key = this._gen_key(params.modelName, params.actionId);
        const forceReload = params.forceReload !== false && config.isDebug('assets');
        if (forceReload || !this._cache.filters[key]) {
            this._cache.filters[key] = rpc.query({
                args: [params.modelName, params.actionId],
                kwargs: {
                    context: params.context || {},
                    // get_context() de dataset
                },
                model: 'ir.filters',
                method: 'get_filters',
            }).guardedCatch(() => this._invalidate('filters', key));
        }
        return this._cache.filters[key];
    },

    /**
     * Calls 'create_or_replace' on 'ir_filters'.
     *
     * @param {Object} [filter] the filter description
     * @return {Promise} resolved with the id of the created or replaced filter
     */
    create_filter: function (filter) {
        return rpc.query({
                args: [filter],
                model: 'ir.filters',
                method: 'create_or_replace',
            })
            .then(filterId => {
                const filtersKey = this._gen_key(filter.model_id, filter.action_id);
                this._invalidate('filters', filtersKey);
                return filterId;
            });
    },

    /**
     * Calls 'unlink' on 'ir_filters'.
     *
     * @param {integer} filterId Id of the filter to remove
     * @return {Promise}
     */
    delete_filter: function (filterId) {
        return rpc.query({
                args: [filterId],
                model: 'ir.filters',
                method: 'unlink',
            })
            // Invalidate the whole cache since we have no idea where the filter came from.
            .then(() => this._invalidate('filters'));
    },

    /**
     * Private function that generates a cache key from its arguments
     */
    _gen_key: function () {
        return _.map(Array.prototype.slice.call(arguments), function (arg) {
            if (!arg) {
                return false;
            }
            return _.isObject(arg) ? JSON.stringify(arg) : arg;
        }).join(',');
    },

    /**
     * Invalidate a cache entry or a whole cache section.
     *
     * @private
     * @param {string} section
     * @param {string} key
     */
    _invalidate(section, key) {
        core.bus.trigger("clear_cache", this);
        if (key) {
            delete this._cache[section][key];
        } else {
            this._cache[section] = {};
        }
    },
});

});

odoo.define('web.data_manager', function (require) {
"use strict";

var DataManager = require('web.DataManager');

var data_manager = new DataManager();

return data_manager;

});
