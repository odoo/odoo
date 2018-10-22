odoo.define('web.viewUtils', function () {
"use strict";

var utils = {
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
                var descriptor = _.findWhere(groupedByField.selection, group.value);
                return descriptor && descriptor[0];
            default:
                return group.value;
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
};

return utils;

});
