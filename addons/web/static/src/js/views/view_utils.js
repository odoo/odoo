odoo.define('web.viewUtils', function (require) {
"use strict";

var dom = require('web.dom');
var utils = require('web.utils');

var viewUtils = {
    /**
     * Returns the value of a group dataPoint, i.e. the value of the groupBy
     * field for the records in that group.
     *
     * @param {Object} group dataPoint of type list, corresponding to a group
     * @param {string} groupByField the name of the groupBy field
     * @returns {string | integer | false}
     */
    getGroupValue: function (group, groupByField) {
        var groupedByField = group.fields[groupByField];
        switch (groupedByField.type) {
            case 'many2one':
                return group.res_id || false;
            case 'selection':
                var descriptor = _.find(groupedByField.selection, function (option) {
                    return option[1] === group.value;
                });
                return descriptor && descriptor[0];
            case 'char':
            case 'boolean':
                return group.value;
            default:
                return false; // other field types are not handled
        }
    },
    /**
     * Generates a local storage key for optional fields in list views. The
     * purpose of this key is to uniquely identify a list view and its fields
     * (so it should be different after installing a module, if that module adds
     * (or removes) fields in the view).
     *
     * For main list views, the key looks like:
     *   'optional_fields,<modelName>,<viewType>,<viewId>,<fields>'
     * For x2many list views, the key looks like:
     *   'optional_fields,<modelName>,<viewType>,<viewId>,<x2mFieldName>,
     *   <subViewType>,<subViewId>,<fields>'
     *
     * In both cases, <fields> is the (comma-separated) list of fields in the
     * list view, sorted by name.
     *
     * For now, <subViewType> is always 'list', and <viewType> is either 'list'
     * (when this is a main list view) or 'form' (when this is a x2m list view).
     * However, having them in the key would ease the generalization of the
     * optional fields feature to other views without breaking existing keys.
     *
     * Note that changing the above specs would make users loose their custom
     * configs.
     *
     * @param {Object} keyParts
     * @param {string} keyParts.model
     * @param {string[]} keyParts.fields
     * @param {integer} [keyParts.viewId]
     * @param {string} [keyParts.relationalField]
     * @param {string} [keyParts.subViewType]
     * @param {integer} [keyParts.subViewId]
     * @returns {string}
     */
    getOptionalFieldsStorageKey: function (keyParts) {
        let parts = ['model', 'viewType', 'viewId'];
        if (keyParts.relationalField) {
            parts = parts.concat(['relationalField', 'subViewType', 'subViewId']);
        }
        const viewPart = parts.map(part => keyParts[part] || 'undefined').join(',');
        const fieldsPart = keyParts.fields.sort((a, b) => a < b ? -1 : 1).join(',');
        return `optional_fields,${viewPart},${fieldsPart}`;
    },
    /**
     * States whether or not the quick create feature is available for the given
     * datapoint, depending on its groupBy field.
     *
     * @param {Object} list dataPoint of type list
     * @returns {Boolean} true iff the kanban quick create feature is available
     */
    isQuickCreateEnabled: function (list) {
        var groupByField = list.groupedBy[0] && list.groupedBy[0].split(':')[0];
        if (!groupByField) {
            return false;
        }
        var availableTypes = ['char', 'boolean', 'many2one', 'selection'];
        if (!_.contains(availableTypes, list.fields[groupByField].type)) {
            return false;
        }
        return true;
    },
    /**
     * @param {string} arch view arch
     * @returns {Object} parsed arch
     */
    parseArch: function (arch) {
        var doc = $.parseXML(arch).documentElement;
        var stripWhitespaces = doc.nodeName.toLowerCase() !== 'kanban';
        return utils.xml_to_json(doc, stripWhitespaces);
    },
    /**
     * Renders a button according to a given arch node element.
     *
     * @param {Object} node
     * @param {Object} [options]
     * @param {string} [options.extraClass]
     * @param {boolean} [options.textAsTitle=false]
     * @returns {jQuery}
     */
    renderButtonFromNode: function (node, options) {
        var btnOptions = {
            attrs: _.omit(node.attrs, 'icon', 'string', 'type', 'attrs', 'modifiers', 'options', 'effect'),
            icon: node.attrs.icon,
        };
        if (options && options.extraClass) {
            var classes = btnOptions.attrs.class ? btnOptions.attrs.class.split(' ') : [];
            btnOptions.attrs.class = _.uniq(classes.concat(options.extraClass.split(' '))).join(' ');
        }
        var str = (node.attrs.string || '').replace(/_/g, '');
        if (str) {
            if (options && options.textAsTitle) {
                btnOptions.attrs.title = str;
            } else {
                btnOptions.text = str;
            }
        }
        return dom.renderButton(btnOptions);
    },
};

return viewUtils;

});
