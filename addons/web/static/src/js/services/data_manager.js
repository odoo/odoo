odoo.define('web.DataManager', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');
var pyeval = require('web.pyeval');
var session = require('web.session');
var utils = require('web.utils');

return core.Class.extend({
    init: function () {
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
            return _.mapObject(views, function (view, viewType) {
                return _.extend(view, self._processFieldsView({
                    type: viewType,
                    arch: view.arch,
                    fields: view.fields,
                }));
            });
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
            this._cache.filters[key] = session.rpc('/web/dataset/call_kw/ir.filters/get_filters', {
                args: [dataset.model, action_id],
                kwargs: {
                    context: dataset.get_context(),
                },
                model: 'ir.filters',
                method: 'get_filters',
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
        return session.rpc('/web/dataset/call_kw/ir.filters/create_or_replace', {
                args: [filter],
                model: 'ir.filters',
                method: 'create_or_replace',
            })
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
        return session.rpc('/web/dataset/call_kw/ir.filters/unlink', {
                args: [filter.id],
                model: 'ir.filters',
                method: 'unlink',
            })
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

    ///////////////////////////////////////////////////////////////

    /**
     * Process a field node, in particular, put a flag on the field to give
     * special directives to the BasicModel.
     *
     * @param {string} viewType
     * @param {Object} field - the field properties
     * @param {Object} attrs - the field attributes (from the xml)
     * @returns {Object} attrs
     */
    _processField: function (viewType, field, attrs) {
        var self = this;
        attrs.Widget = this._getFieldWidgetClass(viewType, field, attrs);

        if (!_.isObject(attrs.options)) { // parent arch could have already been processed (TODO this should not happen)
            attrs.options = attrs.options ? pyeval.py_eval(attrs.options) : {};
        }

        if (attrs.on_change && !field.onChange) {
            field.onChange = "1";
        }

        if (field.views) {
            // process the inner fields_view as well to find the fields they use.
            // register those fields' description directly on the view.
            // for those inner views, the list of all fields isn't necessary, so
            // basically the field_names will be the keys of the fields obj.
            // don't use _ to iterate on fields in case there is a 'length' field,
            // as _ doesn't behave correctly when there is a length key in the object
            attrs.views = {};
            _.each(field.views, function (innerFieldsView, viewType) {
                innerFieldsView.type = viewType;
                attrs.views[viewType] = self._processFieldsView(_.extend({}, innerFieldsView));
            });
            delete field.views;
        }

        if (field.type === 'one2many' || field.type === 'many2many') {
            if (attrs.Widget.prototype.useSubview) {
                if (!attrs.views) {
                    attrs.views = {};
                }
                var mode = attrs.mode;
                if (!mode) {
                    if (attrs.views.tree && attrs.views.kanban) {
                        mode = 'tree';
                    } else if (!attrs.views.tree && attrs.views.kanban) {
                        mode = 'kanban';
                    } else {
                        mode = 'tree,kanban';
                    }
                } else {
                    mode = 'tree,kanban';
                }
                if (mode.indexOf(',') !== -1) {
                    mode = config.device.size_class !== config.device.SIZES.XS ? 'tree' : 'kanban';
                }
                if (mode === 'tree') {
                    mode = 'list';
                    if (!attrs.views.list && attrs.views.tree) {
                        attrs.views.list = attrs.views.tree;
                    }
                }
                attrs.mode = mode;
            }
            if (attrs.Widget.prototype.fetchSubFields) {
                attrs.relatedFields = {
                    display_name: {type: 'char'},
                    //id: {type: 'integer'},
                };
                attrs.fieldsInfo = {display_name: {}, id: {}};
                if (attrs.color || 'color') {
                    attrs.relatedFields[attrs.color || 'color'] = {type: 'int'};
                    attrs.fieldsInfo.color = {};
                }
            }
        }
        return attrs;
    },
    /**
     * Visit all nodes in the arch field and process each fields
     *
     * @param {string} viewType
     * @param {Object} arch
     * @param {Object} fields
     * @returns {Object} fieldsInfo
     */
    _processFields: function (viewType, arch, fields) {
        var self = this;
        var fieldsInfo = Object.create(null);
        utils.traverse(arch, function (node) {
            if (typeof node === 'string') {
                return false;
            }
            if (node.tag === 'field') {
                fieldsInfo[node.attrs.name] = self._processField(viewType,
                    fields[node.attrs.name], node.attrs ? _.clone(node.attrs) : {});
                return false;
            }
            return node.tag !== 'arch';
        });
        return fieldsInfo;
    },
    /**
     * Visit all nodes in the arch field and process each fields and inner views
     *
     * @param {Object} viewInfo
     * @param {Object} viewInfo.arch
     * @param {Object} viewInfo.fields
     * @returns {Object} viewInfo
     */
    _processFieldsView: function (viewInfo) {
        viewInfo.fieldsInfo = this._processFields(viewInfo.type, viewInfo.arch, viewInfo.fields);
        // by default display fetch display_name and id
        if (!viewInfo.fields.display_name) {
            viewInfo.fields.display_name = {type: 'char'};
            viewInfo.fieldsInfo.display_name = {};
        }
        utils.deepFreeze(viewInfo.fields);
        return viewInfo;
    },
    /**
     * Returns the AbstractField specialization that should be used for the
     * given field informations. If there is no mentioned specific widget to
     * use, determine one according the field type.
     *
     * @param {string} viewType
     * @param {Object} field
     * @param {Object} attrs
     * @returns {function|null} AbstractField specialization Class
     */
    _getFieldWidgetClass: function (viewType, field, attrs) {
        var Widget;
        if (attrs.widget) {
            Widget = fieldRegistry.getAny([viewType + "." + attrs.widget, attrs.widget]);
            if (!Widget) {
                console.warn("Missing widget: ", attrs.widget, " for field", attrs.name, "of type", field.type);
            }
        }
        return Widget || fieldRegistry.getAny([viewType + "." + field.type, field.type, "abstract"]);
    },
});

});

odoo.define('web.data_manager', function (require) {
"use strict";

var DataManager = require('web.DataManager');

var data_manager = new DataManager();

return data_manager;

});
