odoo.define('web.BasicView', function (require) {
"use strict";

/**
 * The BasicView is an abstract class designed to share code between views that
 * want to use a basicModel.  As of now, it is the form view, the list view and
 * the kanban view.
 *
 * The main focus of this class is to process the arch and extract field
 * attributes, as well as some other useful informations.
 */

var AbstractView = require('web.AbstractView');
var BasicController = require('web.BasicController');
var BasicModel = require('web.BasicModel');
var config = require('web.config');
var fieldRegistry = require('web.field_registry');
var fieldRegistryOwl = require('web.field_registry_owl');
var pyUtils = require('web.py_utils');
var utils = require('web.utils');
const widgetRegistry = require('web.widget_registry');
const widgetRegistryOwl = require('web.widgetRegistry');

const { Component } = owl;

var BasicView = AbstractView.extend({
    config: _.extend({}, AbstractView.prototype.config, {
        Model: BasicModel,
        Controller: BasicController,
    }),
    viewType: undefined,
    /**
     * process the fields_view to find all fields appearing in the views.
     * list those fields' name in this.fields_name, which will be the list
     * of fields read when data is fetched.
     * this.fields is the list of all field's description (the result of
     * the fields_get), where the fields appearing in the fields_view are
     * augmented with their attrs and some flags if they require a
     * particular handling.
     *
     * @param {Object} viewInfo
     * @param {Object} params
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        this.fieldsInfo = {};
        this.fieldsInfo[this.viewType] = this.fieldsView.fieldsInfo[this.viewType];

        this.rendererParams.viewType = this.viewType;
        this.rendererParams.viewEditable = this.controllerParams.activeActions.edit;

        this.controllerParams.confirmOnDelete = true;
        this.controllerParams.archiveEnabled = 'active' in this.fields ? !this.fields.active.readonly
                                             : 'x_active' in this.fields ? !this.fields.x_active.readonly
                                             : false;
        this.controllerParams.hasButtons =
                'action_buttons' in params ? params.action_buttons : true;
        this.controllerParams.viewId = viewInfo.view_id;

        this.loadParams.fieldsInfo = this.fieldsInfo;
        this.loadParams.fields = this.fields;
        this.loadParams.limit = parseInt(this.arch.attrs.limit, 10) || params.limit;
        this.loadParams.parentID = params.parentID;
        this.loadParams.viewType = this.viewType;
        this.recordID = params.recordID;

        this.model = params.model;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns the AbstractField specialization that should be used for the
     * given field informations. If there is no mentioned specific widget to
     * use, determines one according the field type.
     *
     * @private
     * @param {string} viewType
     * @param {Object} field
     * @param {Object} attrs
     * @returns {function|null} AbstractField specialization Class
     */
    _getFieldWidgetClass: function (viewType, field, attrs) {
        var FieldWidget;
        if (attrs.widget === "boolean" || (!attrs.widget && field.type === "boolean")) {
            FieldWidget = fieldRegistry.getAny([viewType + ".boolean", "boolean"]);
        } else if (attrs.widget) {
            FieldWidget = fieldRegistry.getAny([viewType + "." + attrs.widget, attrs.widget]) ||
                fieldRegistryOwl.getAny([viewType + "." + attrs.widget, attrs.widget]);
            if (!FieldWidget) {
                console.warn("Missing widget: ", attrs.widget, " for field", attrs.name, "of type", field.type);
            }
        } else if (viewType === 'kanban' && field.type === 'many2many') {
            // we want to display the widget many2manytags in kanban even if it
            // is not specified in the view
            FieldWidget = fieldRegistry.get('kanban.many2many_tags');
        }
        return FieldWidget ||
            fieldRegistryOwl.getAny([viewType + "." + field.type, field.type, "abstract"]) ||
            fieldRegistry.getAny([viewType + "." + field.type, field.type, "abstract"]);
    },
    /**
     * In some cases, we already have a preloaded record
     *
     * @override
     * @private
     * @returns {Promise}
     */
    _loadData: async function (model) {
        if (this.recordID) {
            // Add the fieldsInfo of the current view to the given recordID,
            // as it will be shared between two views, and it must be able to
            // handle changes on fields that are only on this view.
            await model.addFieldsInfo(this.recordID, {
                fields: this.fields,
                fieldInfo: this.fieldsInfo[this.viewType],
                viewType: this.viewType,
            });

            var record = model.get(this.recordID);
            var viewType = this.viewType;
            var viewFields = Object.keys(record.fieldsInfo[viewType]);
            var fieldNames = _.difference(viewFields, Object.keys(record.data));
            var fieldsInfo = record.fieldsInfo[viewType];

            // Suppose that in a form view, there is an x2many list view with
            // a field F, and that F is also displayed in the x2many form view.
            // In this case, F is represented in record.data (as it is known by
            // the x2many list view), but the loaded information may not suffice
            // in the form view (e.g. if field is a many2many list in the form
            // view, or if it is displayed by a widget requiring specialData).
            // So when this happens, F is added to the list of fieldNames to fetch.
            _.each(viewFields, (name) => {
                if (!_.contains(fieldNames, name)) {
                    var fieldType = record.fields[name].type;
                    var fieldInfo = fieldsInfo[name];

                    // SpecialData case: field requires specialData that haven't
                    // been fetched yet.
                    if (fieldInfo.Widget) {
                        var requiresSpecialData = fieldInfo.Widget.prototype.specialData;
                        if (requiresSpecialData && !(name in record.specialData)) {
                            fieldNames.push(name);
                            return;
                        }
                    }

                    // X2Many case: field is an x2many displayed as a list or
                    // kanban view, but the related fields haven't been loaded yet.
                    if ((fieldType === 'one2many' || fieldType === 'many2many')) {
                        if (!('fieldsInfo' in record.data[name])) {
                            fieldNames.push(name);
                        } else {
                            var x2mFieldInfo = record.fieldsInfo[this.viewType][name];
                            var viewType = x2mFieldInfo.viewType || x2mFieldInfo.mode;
                            var knownFields = Object.keys(record.data[name].fieldsInfo[record.data[name].viewType] || {});
                            var newFields = Object.keys(record.data[name].fieldsInfo[viewType] || {});
                            if (_.difference(newFields, knownFields).length) {
                                fieldNames.push(name);
                            }

                            if (record.data[name].viewType === 'default') {
                                // Use case: x2many (tags) in x2many list views
                                // When opening the x2many record form view, the
                                // x2many will be reloaded but it may not have
                                // the same fields (ex: tags in list and list in
                                // form) so we need to merge the fieldsInfo to
                                // avoid losing the initial fields (display_name)
                                var fieldViews = fieldInfo.views || fieldInfo.fieldsInfo || {};
                                var defaultFieldInfo = record.data[name].fieldsInfo.default;
                                _.each(fieldViews, function (fieldView) {
                                    _.each(fieldView.fieldsInfo, function (x2mFieldInfo) {
                                        _.defaults(x2mFieldInfo, defaultFieldInfo);
                                    });
                                });
                            }
                        }
                    }
                    // Many2one: context is not the same between the different views
                    // this means the result of a name_get could differ
                    if (fieldType === 'many2one') {
                        if (JSON.stringify(record.data[name].context) !==
                                JSON.stringify(fieldInfo.context)) {
                            fieldNames.push(name);
                        }
                    }
                }
            });

            var def;
            if (fieldNames.length) {
                if (model.isNew(record.id)) {
                    def = model.generateDefaultValues(record.id, {
                        fieldNames: fieldNames,
                        viewType: viewType,
                    });
                } else {
                    def = model.reload(record.id, {
                        fieldNames: fieldNames,
                        keepChanges: true,
                        viewType: viewType,
                    });
                }
            }
            return Promise.resolve(def).then(function () {
                const handle = record.id;
                return { state: model.get(handle), handle };
            });
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Traverses the arch and calls '_processNode' on each of its nodes.
     *
     * @private
     * @param {Object} arch a parsed arch
     * @param {Object} fv the fieldsView Object, in which _processNode can
     *   access and add information (like the fields' attributes in the arch)
     */
    _processArch: function (arch, fv) {
        var self = this;
        utils.traverse(arch, function (node) {
            return self._processNode(node, fv);
        });
    },
    /**
     * Processes a field node, in particular, put a flag on the field to give
     * special directives to the BasicModel.
     *
     * @private
     * @param {string} viewType
     * @param {Object} field - the field properties
     * @param {Object} attrs - the field attributes (from the xml)
     * @returns {Object} attrs
     */
    _processField: function (viewType, field, attrs) {
        var self = this;
        attrs.Widget = this._getFieldWidgetClass(viewType, field, attrs);

        // process decoration attributes
        _.each(attrs, function (value, key) {
            if (key.startsWith('decoration-')) {
                attrs.decorations = attrs.decorations || [];
                attrs.decorations.push({
                    name: key,
                    expression: pyUtils._getPyJSAST(value),
                });
            }
        });

        if (!_.isObject(attrs.options)) { // parent arch could have already been processed (TODO this should not happen)
            attrs.options = attrs.options ? pyUtils.py_eval(attrs.options) : {};
        }

        if (attrs.on_change && attrs.on_change !== "0" && !field.onChange) {
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
                attrs.views[viewType] = self._processFieldsView(innerFieldsView, viewType);
            });
        }

        attrs.views = attrs.views || {};

        // Keep compatibility with 'tree' syntax
        attrs.mode = attrs.mode === 'tree' ? 'list' : attrs.mode;
        if (!attrs.views.list && attrs.views.tree) {
            attrs.views.list = attrs.views.tree;
        }

        if (field.type === 'one2many' || field.type === 'many2many') {
            if (attrs.Widget.prototype.useSubview) {
                var mode = attrs.mode;
                if (!mode) {
                    if (attrs.views.list && !attrs.views.kanban) {
                        mode = 'list';
                    } else if (!attrs.views.list && attrs.views.kanban) {
                        mode = 'kanban';
                    } else {
                        mode = 'list,kanban';
                    }
                }
                if (mode.indexOf(',') !== -1) {
                    mode = config.device.isMobile ? 'kanban' : 'list';
                }
                attrs.mode = mode;
                if (mode in attrs.views) {
                    var view = attrs.views[mode];
                    this._processSubViewAttrs(view, attrs);
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
     * Overrides to process the fields, and generate fieldsInfo which contains
     * the description of the fields in view, with their attrs in the arch.
     *
     * @override
     * @private
     * @param {Object} fieldsView
     * @param {string} fieldsView.arch
     * @param {Object} fieldsView.fields
     * @param {string} [viewType] by default, this.viewType
     * @returns {Object} the processed fieldsView with extra key 'fieldsInfo'
     */
    _processFieldsView: function (fieldsView, viewType) {
        var fv = this._super.apply(this, arguments);

        viewType = viewType || this.viewType;
        fv.type = viewType;
        fv.fieldsInfo = Object.create(null);
        fv.fieldsInfo[viewType] = Object.create(null);

        this._processArch(fv.arch, fv);

        return fv;
    },
    /**
     * Processes a node of the arch (mainly nodes with tagname 'field'). Can
     * be overridden to handle other tagnames.
     *
     * @private
     * @param {Object} node
     * @param {Object} fv the fieldsView
     * @param {Object} fv.fieldsInfo
     * @param {Object} fv.fieldsInfo[viewType] fieldsInfo of the current viewType
     * @param {Object} fv.viewFields the result of a fields_get extend with the
     *   fields returned with the fields_view_get for the current viewType
     * @param {string} fv.viewType
     * @returns {boolean} false iff subnodes must not be visited.
     */
    _processNode: function (node, fv) {
        const viewType = fv.type;
        const fieldsInfo = fv.fieldsInfo[viewType];
        const fields = fv.viewFields;

        const _addFieldDependencies = (deps) => {
            for (const dependencyName in deps) {
                const dependencyDict = { name: dependencyName, type: deps[dependencyName].type };
                if (!(dependencyName in fieldsInfo)) {
                    fieldsInfo[dependencyName] = _.extend({}, dependencyDict, {
                        options: deps[dependencyName].options || {},
                    });
                }
                if (!(dependencyName in fields)) {
                    fields[dependencyName] = dependencyDict;
                }

                if (fv.fields && !(dependencyName in fv.fields)) {
                    fv.fields[dependencyName] = dependencyDict;
                }
            }
        };

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
            fieldsInfo[node.attrs.name] = this._processField(viewType,
                fields[node.attrs.name], node.attrs ? _.clone(node.attrs) : {});

            if (fieldsInfo[node.attrs.name].fieldDependencies) {
                var deps = fieldsInfo[node.attrs.name].fieldDependencies;
                _addFieldDependencies(deps);
            }
            return false;
        }
        // custom widget may have fieldDependencies so add it to fields of fields_view
        if (node.tag === 'widget') {
            const Widget = widgetRegistryOwl.get(node.attrs.name) || widgetRegistry.get(node.attrs.name);
            const legacy = !(Widget.prototype instanceof Component);
            let deps;
            if (legacy && Widget.prototype.fieldDependencies) {
                deps = Widget.prototype.fieldDependencies;
            } else if (Widget.fieldDependencies) {
                deps = Widget.fieldDependencies;
            }
            if (deps) {
                _addFieldDependencies(deps);
            }
            return false;
        }
        return node.tag !== 'arch';
    },
    /**
     * Processes in place the subview attributes (in particular,
     * `default_order``and `column_invisible`).
     *
     * @private
     * @param {Object} view - the field subview
     * @param {Object} attrs - the field attributes (from the xml)
     */
    _processSubViewAttrs: function (view, attrs) {
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
    },
});

return BasicView;

});
