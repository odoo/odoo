odoo.define('web.DataManager', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.DataModel');
var session = require('web.session');
var utils = require('web.utils');

return core.Class.extend({
    init: function () {
        this.Filters = new Model('ir.filters');
        this._init_cache();
    },

    _init_cache: function () {
        this._cache = {
            actions: {},
            fields_views: {},
            filters: {},
            views: {},
        };
    },

    /**
     * Invalidates the whole cache
     * Suggestion: could be refined to invalidate some part of the cache
     */
    invalidate: function () {
        this._init_cache();
    },

    /**
     * Loads an action from its id or xmlid.
     *
     * @param {int|string} [action_id] the action id or xmlid
     * @param {Object} [additional_context] used to load the action
     * @return {Deferred} resolved with the action whose id or xmlid is action_id
     */
    load_action: function (action_id, additional_context) {
        var self = this;
        var key = this._gen_key(action_id, additional_context || {});

        if (!this._cache.actions[key]) {
            this._cache.actions[key] = session.rpc("/web/action/load", {
                action_id: action_id,
                additional_context : additional_context,
            }).then(function (action) {
                self._cache.actions[key] = action.no_cache ? null : self._cache.actions[key];
                return action;
            }, this._invalidate.bind(this, this._cache.actions, key));
        }

        return this._cache.actions[key].then(function (action) {
            return $.extend(true, {}, action);
        });
    },

    /**
     * Loads various information concerning views: fields_view for each view,
     * the fields of the corresponding model, and optionally the filters.
     *
     * @param {Object} [dataset] the dataset for which the views are loaded
     * @param {Array} [views_descr] array of [view_id, view_type]
     * @param {Object} [options] dictionnary of various options:
     *     - options.load_filters: whether or not to load the filters,
     *     - options.action_id: the action_id (required to load filters),
     *     - options.toolbar: whether or not a toolbar will be displayed,
     * @return {Deferred} resolved with the requested views information
     */
    load_views: function (params, options) {
        var self = this;

        var model = params.model;
        var context = params.context;
        var views_descr = params.views_descr;
        var key = this._gen_key(model, views_descr, options || {}, context);

        if (!this._cache.views[key]) {
            // Don't load filters if already in cache
            var filters_key;
            if (options.load_filters) {
                filters_key = this._gen_key(model, options.action_id);
                options.load_filters = !this._cache.filters[filters_key];
            }

            this._cache.views[key] = session.rpc('/web/dataset/call_kw/' + model + '/load_views', {
                args: [],
                kwargs: {
                    views: views_descr,
                    options: options,
                    context: context.eval(),
                },
                model: model,
                method: 'load_views',
            }).then(function (result) {
                // Postprocess fields_views and insert them into the fields_views cache
                result.fields_views = _.mapObject(result.fields_views, self._postprocess_fvg.bind(self));
                _.each(result.fields_views, function (fields_view) {
                    _.defaults(fields_view.fields, result.fields);
                });
                _.each(views_descr, function (view_descr) {
                    var toolbar = options.toolbar && view_descr[1] !== 'search';
                    var fv_key = self._gen_key(model, view_descr[0], view_descr[1], toolbar, context);
                    self._cache.fields_views[fv_key] = $.when(result.fields_views[view_descr[1]]);
                });

                // Insert filters, if any, into the filters cache
                if (result.filters) {
                    self._cache.filters[filters_key] = $.when(result.filters);
                }

                return result.fields_views;
            }, this._invalidate.bind(this, this._cache.views, key));
        }

        return this._cache.views[key].then(function (views) {
            return $.extend(true, {}, views);
        });
    },

    /**
     * Loads the filters of a given model and optional action id.
     *
     * @param {Object} [dataset] the dataset for which the filters are loaded
     * @param {int} [action_id] the id of the action (optional)
     * @return {Deferred} resolved with the requested filters
     */
    load_filters: function (dataset, action_id) {
        var key = this._gen_key(dataset.model, action_id);
        if (!this._cache.filters[key]) {
            this._cache.filters[key] = this.Filters.call('get_filters', [dataset.model, action_id], {
                context: dataset.get_context(),
            }).fail(this._invalidate.bind(this, this._cache.filters, key));
        }
        return this._cache.filters[key];
    },

    /**
     * Calls 'create_or_replace' on 'ir_filters'.
     *
     * @param {Object} [filter] the filter description
     * @return {Deferred} resolved with the id of the created or replaced filter
     */
    create_filter: function (filter) {
        var self = this;
        return this.Filters
            .call('create_or_replace', [filter])
            .then(function (filter_id) {
                var key = [
                    filter.model_id,
                    filter.action_id || false,
                ].join(',');
                self._invalidate(self._cache.filters, key);
                return filter_id;
            });
    },

    /**
     * Calls 'unlink' on 'ir_filters'.
     *
     * @param {Object} [filter] the description of the filter to remove
     * @return {Deferred}
     */
    delete_filter: function (filter) {
        var self = this;
        return this.Filters
            .call('unlink', [filter.id])
            .then(function () {
                self._cache.filters = {}; // invalidate cache
            });
    },

    /**
     * Private function that postprocesses fields_view (mainly parses the arch attribute)
     */
    _postprocess_fvg: function (fields_view) {
        var self = this;

        // Parse arch
        var doc = $.parseXML(fields_view.arch).documentElement;
        fields_view.arch = utils.xml_to_json(doc, (doc.nodeName.toLowerCase() !== 'kanban'));

        // Special case for id's
        if ('id' in fields_view.fields) {
            var id_field = fields_view.fields.id;
            id_field.original_type = id_field.type;
            id_field.type = 'id';
        }

        // Process inner views (one2manys)
        _.each(fields_view.fields, function(field) {
            _.each(field.views || {}, function(view) {
                self._postprocess_fvg(view);
            });
        });

        return fields_view;
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
     * Private function that invalidates a cache entry
     */
    _invalidate: function (cache, key) {
        delete cache[key];
    },
});

});

odoo.define('web.data_manager', function (require) {
"use strict";

var DataManager = require('web.DataManager');

var data_manager = new DataManager();

return data_manager;

});
