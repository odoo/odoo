odoo.define('web.DataManager', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');
var pyeval = require('web.pyeval');
var rpc = require('web.rpc');
var utils = require('web.utils');

return core.Class.extend({
    init: function () {
        this._init_cache();
        core.bus.on('clear_cache', this, this.invalidate.bind(this));
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
            this._cache.actions[key] = rpc.query({
                route: "/web/action/load",
                params: {
                    action_id: action_id,
                    additional_context : additional_context,
                },
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
     * @param {Object} params
     * @param {String} params.model
     * @param {Object} params.context
     * @param {Array} params.views_descr array of [view_id, view_type]
     * @param {Object} [options] dictionary of various options:
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

            this._cache.views[key] = rpc.query({
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
                self.processViews(result.fields_views, result.fields);
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

        return this._cache.views[key];
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
            this._cache.filters[key] = rpc.query({
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
        return rpc.query({
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
        return rpc.query({
                args: [filter.id],
                model: 'ir.filters',
                method: 'unlink',
            })
            .then(function () {
                self._cache.filters = {}; // invalidate cache
            });
    },

    /**
     * Processes fields and fields_views. For each field, writes its name inside
     * the field description to make it self-contained. For each fields_view,
     * completes its fields with the missing ones.
     *
     * @param {Object} fieldsViews object of fields_views (keys are view types)
     * @param {Object} fields all the fields of the model
     */
    processViews: function (fieldsViews, fields) {
        var fieldName, fieldsView, viewType;
        // write the field name inside the description for all fields
        for (fieldName in fields) {
            fields[fieldName].name = fieldName;
        }
        for (viewType in fieldsViews) {
            fieldsView = fieldsViews[viewType];
            // write the field name inside the description for fields in view
            for (fieldName in fieldsView.fields) {
                fieldsView.fields[fieldName].name = fieldName;
            }
            // complete fields (in view) with missing ones
            _.defaults(fieldsView.fields, fields);
            // process the fields_view
            _.extend(fieldsView, this._processFieldsView({
                type: viewType,
                arch: fieldsView.arch,
                fields: fieldsView.fields,
            }));
        }
    },

    /**
     * Private function that postprocesses fields_view (mainly parses the arch attribute)
     */
    _postprocess_fvg: function (fields_view) {
        var self = this;

        // Parse arch
        var doc = $.parseXML(fields_view.arch).documentElement;
        fields_view.arch = utils.xml_to_json(doc, (doc.nodeName.toLowerCase() !== 'kanban'));

        // Process inner views (x2manys)
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

        // the relational data of invisible relational fields should not be
        // fetched (e.g. name_gets of invisible many2ones), at least those that
        // are always invisible.
        // the invisible attribute of a field is supposed to be static ("1" in
        // general), but not totally as it may use keys of the context
        // ("context.get('some_key')"). It is evaluated server-side, and the
        // result is put inside the modifiers as a value of the '(column_)invisible'
        // key, and the raw value is left in the invisible attribute (it is used
        // in debug mode for informational purposes).
        // this should change, for instance the server might set the evaluated
        // value in invisible, which could then be seen as static by the client,
        // and add another key in debug mode containing the raw value.
        // for now, we look inside the modifiers and consider the value only if
        // it is static (=== true),
        if (attrs.modifiers.invisible === true || attrs.modifiers.column_invisible === true) {
            attrs.__no_fetch = true;
        }

        if (!_.isEmpty(field.views)) {
            // process the inner fields_view as well to find the fields they use.
            // register those fields' description directly on the view.
            // for those inner views, the list of all fields isn't necessary, so
            // basically the field_names will be the keys of the fields obj.
            // don't use _ to iterate on fields in case there is a 'length' field,
            // as _ doesn't behave correctly when there is a length key in the object
            attrs.views = {};
            _.each(field.views, function (innerFieldsView, viewType) {
                viewType = viewType === 'tree' ? 'list' : viewType;
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
                if (mode in attrs.views) {
                    var view = attrs.views[mode];
                    var defaultOrder = view.arch.attrs.default_order;
                    if (defaultOrder) {
                        // process the default_order, which is like 'name,id desc'
                        // but we need it like [{name: 'name', asc: true}, {name: 'id', asc: false}]
                        attrs.orderedBy = _.map(defaultOrder.split(','), function (order) {
                            order = order.trim().split(' ');
                            return {name: order[0], asc: order[1] !== 'desc'};
                        });
                    } else {
                        // if there is a field with widget `handle`, the x2many
                        // needs to be ordered by this field to correctly display
                        // the records
                        var handleField = _.find(view.arch.children, function (child) {
                            return child.attrs && child.attrs.widget === 'handle';
                        });
                        if (handleField) {
                            attrs.orderedBy = [{name: handleField.attrs.name, asc: true}];
                        }
                    }

                    attrs.columnInvisibleFields = {};
                    _.each(view.arch.children, function (child) {
                        if (child.attrs && child.attrs.modifiers) {
                            attrs.columnInvisibleFields[child.attrs.name] =
                                child.attrs.modifiers.column_invisible || false;
                        }
                    });
                }
            }
            if (attrs.Widget.prototype.fieldsToFetch) {
                attrs.viewType = 'default';
                attrs.relatedFields = _.extend({}, attrs.Widget.prototype.fieldsToFetch);
                attrs.fieldsInfo = {
                    default: _.mapObject(attrs.Widget.prototype.fieldsToFetch, function () {
                        return {};
                    }),
                };
                if (attrs.options.color_field) {
                    // used by m2m tags
                    attrs.relatedFields[attrs.options.color_field] = { type: 'integer' };
                    attrs.fieldsInfo.default[attrs.options.color_field] = {};
                }
            }
        }

        if (attrs.Widget.prototype.fieldDependencies) {
            attrs.fieldDependencies = attrs.Widget.prototype.fieldDependencies;
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
            if (!_.isObject(node.attrs.modifiers)) {
                node.attrs.modifiers = node.attrs.modifiers ? JSON.parse(node.attrs.modifiers) : {};
            }
            if (!_.isObject(node.attrs.options) && node.tag === 'button') {
                node.attrs.options = node.attrs.options ? JSON.parse(node.attrs.options) : {};
            }
            if (node.tag === 'field') {
                fieldsInfo[node.attrs.name] = self._processField(viewType,
                    fields[node.attrs.name], node.attrs ? _.clone(node.attrs) : {});

                if (fieldsInfo[node.attrs.name].fieldDependencies) {
                    var deps = fieldsInfo[node.attrs.name].fieldDependencies;
                    for (var dependency_name in deps) {
                        var dependency_dict = {name: dependency_name, type: deps[dependency_name].type};
                        if (!(dependency_name in fieldsInfo)) {
                            fieldsInfo[dependency_name] = _.extend({}, dependency_dict, {options: deps[dependency_name].options || {}});
                        }
                        if (!(dependency_name in fields)) {
                            fields[dependency_name] = dependency_dict;
                        }
                    }
                }
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
        var viewFields = this._processFields(viewInfo.type, viewInfo.arch, viewInfo.fields);
        viewInfo.fieldsInfo = {};
        viewInfo.fieldsInfo[viewInfo.type] = viewFields;
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
        } else if (viewType === 'kanban' && field.type === 'many2many') {
            // we want to display the widget many2manytags in kanban even if it
            // is not specified in the view
            Widget = fieldRegistry.get('kanban.many2many_tags');
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
