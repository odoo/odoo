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
        var view_fields = result.view_fields;
        var fieldNames = _.keys(view_fields);
        fields = _.defaults(view_fields, fields);
        var self = this;
        // process the inner fields_view as well to find the fields they use.
        // register those fields' description directly on the view.
        // for those inner views, the list of all fields isn't necessary, so
        // basically the field_names will be the keys of the fields obj.
        // don't use _ to iterate on fields in case there is a 'length' field,
        // as _ doesn't behave correctly when there is a length key in the object
        for (var field_name in fields) {
            var field = fields[field_name];
            _.each(field.views, function (inner_fields_view) {
                result = self._processFieldsView(inner_fields_view.arch, inner_fields_view.fields);
                inner_fields_view.fieldAttrs = result.fieldAttrs;
                inner_fields_view.fields = result.view_fields;
            });
            if (field.type === 'one2many' || field.type === 'many2many') {
                if (field.views && field.views.tree) {
                    field.relatedFields = field.views.tree.fields;
                    field.fieldAttrs = field.views.tree.fieldAttrs;
                    field.limit = 80;
                } else if (field.views && field.views.kanban) {
                    field.relatedFields = field.views.kanban.fields;
                    field.fieldAttrs = field.views.kanban.fieldAttrs;
                    field.limit = 40;
                } else {
                    field.relatedFields = {
                        color: {type: 'int'},
                        display_name: {type: 'char'},
                        id: {type: 'integer'},
                    };
                    field.fieldAttrs = {};
                }
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
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Visit all nodes in the arch field and process each fields
     *
     * @param {Object} arch
     * @param {Object} fields
     * @returns {Object} An object with 2 keys: view_fields and fieldAttrs
     */
    _processFieldsView: function (arch, fields) {
        var self = this;
        var view_fields = Object.create(null);
        var fieldAttrs = Object.create(null);
        traverse(arch, function (node) {
            if (typeof node === 'string') {
                return false;
            }
            if (node.tag === 'field') {
                var attrs = node.attrs || {};
                var field = _.extend({}, fields[node.attrs.name]);
                self._processField(field, node, attrs);
                view_fields[node.attrs.name] = field;
                fieldAttrs[node.attrs.name] = attrs;
                return false;
            }
            return node.tag !== 'arch';
        });
        return {
            view_fields: view_fields,
            fieldAttrs: fieldAttrs,
        };
    },
    /**
     * Process a field node, in particular, put a flag on the field to give
     * special directives to the BasicModel.
     *
     * @param {Object} field
     * @param {Object} node
     * @param {Object} attrs
     */
    _processField: function (field, node, attrs) {
        if (attrs.options) {
            var options = pyeval.py_eval(attrs.options || '{}');
            if (options.always_reload) {
                field.__always_reload = true;
            }
        }
        if (field.type === 'many2one') {
            if (node.attrs.widget === 'statusbar' || node.attrs.widget === 'radio') {
                field.__fetch_status = true;
            } else if (node.attrs.widget === 'selection') {
                field.__fetch_selection = true;
            }
        }
        if (node.attrs.widget === 'many2many_checkboxes') {
            field.__fetch_many2manys = true;
        }
        if (node.attrs.on_change) {
            field.onChange = "1";
        }
    },
});

return BasicView;

});
