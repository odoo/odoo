/** @odoo-module alias=web.viewUtils **/


import * as dom from 'web.dom';
import * as utils from 'web.utils';

var viewUtils = {
    /**
     * Since a date field can have a granularity in a groupby (date_field:granularity),
     * when we require only the field name, we have to split out the
     * eventual granularity
     * 
     * @param {string} groupedBy the groupby with the eventual granularity
     * @returns {string}
     */
    getGroupByField: function(groupedBy) {
        return groupedBy && groupedBy.split(':')[0];
    },
    /**
     * Returns the value of a group dataPoint, i.e. the value of the groupBy
     * field for the records in that group.
     *
     * @param {Object} group dataPoint of type list, corresponding to a group
     * @param {string} groupedBy the value of the groupby, i.e.
     *                           field_name:granularity for date/datetime
     * @returns {string | integer | false}
     */
    getGroupValue: function (group, groupedBy) {
        var groupedByField = group.fields[this.getGroupByField(groupedBy)];
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
            // for a date/datetime field, we take the last moment of the group as the group value
            case 'date':
            case 'datetime':
                const [format, granularity] = groupedByField.type === 'date' ?
                    ["YYYY-MM-DD", 'day'] : ["YYYY-MM-DD HH:mm:ss", 'second'];
                return group.range[groupedBy] ?
                    moment.utc(group.range[groupedBy].to).subtract(1, granularity).format(format) : false;
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
        var groupByField = list.groupedBy[0] && viewUtils.getGroupByField(list.groupedBy[0]);
        if (!groupByField) {
            return false;
        }
        var dateTypes = ['date', 'datetime'];
        if (!list.fields[groupByField].readonly &&
            _.contains(dateTypes, list.fields[groupByField].type)) {
            return list.fieldsInfo && list.fieldsInfo[list.viewType][groupByField] &&
                list.fieldsInfo[list.viewType][groupByField].allowGroupRangeValue;
        }
        var availableTypes = ['char', 'boolean', 'many2one', 'selection'];
        return _.contains(availableTypes, list.fields[groupByField].type);
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

export default viewUtils;
