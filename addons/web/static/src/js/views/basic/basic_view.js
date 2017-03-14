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
var fieldRegistry = require('web.field_registry');
var pyeval = require('web.pyeval');

/**
 * Visit a tree of objects, where each children are in an attribute 'children'.
 * For each children, we call the callback function given in arguments.
 *
 * @todo move this somewhere in web.utils
 *
 * @param {Object} tree an object describing a tree structure
 * @param {function} f a callback
 */
function traverse(tree, f) {
    if (f(tree)) {
        _.each(tree.children, function (c) { traverse(c, f); });
    }
}

var BasicView = AbstractView.extend({
    config: _.extend({}, AbstractView.prototype.config, {
        Model: BasicModel,
        Controller: BasicController,
    }),
    /**
     * process the fields_view to find all fields appearing in the views.
     * list those fields' name in this.fields_name, which will be the list
     * of fields read when data is fetched.
     * this.fields is the list of all field's description (the result of
     * the fields_get), where the fields appearing in the fields_view are
     * augmented with their attrs and some flags if they require a
     * particular handling.
     *
     * @param {Object} arch
     * @param {Object} fields
     * @param {Object} params
     */
    init: function (arch, fields, params) {
        this._super.apply(this, arguments);

        var result = this._processFieldsView(arch, fields);
        var fieldAttrs = result.fieldAttrs;
        var viewFields = result.view_fields;
        var fieldNames = _.keys(viewFields);
        fields = _.defaults(viewFields, fields);
        var self = this;
        // process the inner fields_view as well to find the fields they use.
        // register those fields' description directly on the view.
        // for those inner views, the list of all fields isn't necessary, so
        // basically the field_names will be the keys of the fields obj.
        // don't use _ to iterate on fields in case there is a 'length' field,
        // as _ doesn't behave correctly when there is a length key in the object
        for (var fieldName in fields) {
            var field = fields[fieldName];
            _.each(field.views, function (innerFieldsView) {
                result = self._processFieldsView(innerFieldsView.arch, innerFieldsView.fields);
                innerFieldsView.fieldAttrs = result.fieldAttrs;
                innerFieldsView.fields = result.view_fields;
            });
            if (field.type === 'one2many' || field.type === 'many2many') {
                field.relatedFields = {
                    color: {type: 'int'},
                    display_name: {type: 'char'},
                    id: {type: 'integer'},
                };
                field.fieldAttrs = {};
            }
        }

        this.controllerParams.confirmOnDelete = true;
        this.controllerParams.archiveEnabled = 'active' in fields;
        this.controllerParams.hasButtons =
                'action_buttons' in params ? params.action_buttons : true;

        this.loadParams.fieldAttrs = fieldAttrs;
        this.loadParams.fieldNames = fieldNames;
        this.loadParams.fields = fields;
        this.loadParams.limit = parseInt(arch.attrs.limit, 10) || params.limit;
        this.recordID = params.recordID;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * In some cases, we already have a preloaded record
     *
     * @override
     * @private
     * @returns {Deferred}
     */
    _loadData: function () {
        if (this.recordID) {
            var record = this.model.get(this.recordID);
            var fieldNames = _.difference(record.fieldNames, Object.keys(record.data));
            if (fieldNames.length && !this.model.isNew(record.id)) {
                return this.model.reload(this.recordID, {fieldNames: fieldNames});
            } else {
                return $.when(this.recordID);
            }
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Visit all nodes in the arch field and process each fields
     *
     * @param {Object} arch
     * @param {Object} fields
     * @returns {Object} An object with 2 keys: view_fields and fieldAttrs
     */
    _processFieldsView: function (arch, fields) {
        var self = this;
        var viewFields = Object.create(null);
        var fieldAttrs = Object.create(null);
        traverse(arch, function (node) {
            if (typeof node === 'string') {
                return false;
            }
            if (node.tag === 'field') {
                var attrs = node.attrs ? _.clone(node.attrs) : {};
                var field = _.clone(fields[node.attrs.name]);
                self._processField(field, attrs);
                viewFields[node.attrs.name] = field;
                fieldAttrs[node.attrs.name] = attrs;
                return false;
            }
            return node.tag !== 'arch';
        });
        return {
            view_fields: viewFields,
            fieldAttrs: fieldAttrs,
        };
    },
    /**
     * Process a field node, in particular, put a flag on the field to give
     * special directives to the BasicModel.
     *
     * @param {Object} field - the field properties
     * @param {Object} attrs - the field attributes (from the xml)
     */
    _processField: function (field, attrs) {
        attrs.Widget = this._getFieldWidgetClass(field, attrs);

        if (!_.isObject(attrs.options)) { // parent arch could have already been processed (TODO this should not happen)
            attrs.options = attrs.options ? pyeval.py_eval(attrs.options) : {};
        }

        if (attrs.on_change) {
            field.onChange = "1";
        }
    },

    /**
     * Returns the AbstractField specialization that should be used for the
     * given field informations. If there is no mentioned specific widget to
     * use, determine one according the field type.
     *
     * @param {Object} field
     * @param {Object} attrs
     * @returns {function|null} AbstractField specialization Class
     */
    _getFieldWidgetClass: function (field, attrs) {
        var viewName = this.rendererParams.arch.tag;

        var Widget;
        if (attrs.widget) {
            Widget = fieldRegistry.getAny([viewName + "." + attrs.widget, attrs.widget]);
            if (!Widget) {
                console.warn("Missing widget: ", attrs.widget, " for field", attrs.name, "of type", field.type);
            }
        }
        return Widget || fieldRegistry.getAny([viewName + "." + field.type, field.type, "abstract"]);
    },
});

return BasicView;

});
