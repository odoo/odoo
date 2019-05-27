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
