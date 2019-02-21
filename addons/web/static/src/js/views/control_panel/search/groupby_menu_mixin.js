odoo.define('web.GroupByMenuMixin', function (require) {
"use strict";

var GroupByMenu = require('web.GroupByMenu');
var controlPanelViewParameters = require('web.controlPanelViewParameters');

/**
 * The aim of this mixin is to facilitate the interaction between
 * a view controller and a dropdown menu with its control panel
 * TO DO: the pivot subview has two types of groupbys so that it will not
 * understand the current implementation of this mixin
 *
 * @mixin
 * @name GroupByMenuMixin
 */
var GroupByMenuMixin = {
    init: function () {
        this.custom_events = _.extend({}, this.custom_events, {
            menu_item_clicked: '_onMenuItemClicked',
            item_option_clicked: '_onItemOptionClicked',
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Instantiate a widget GroupByMenu and incorporate it to the control panel
     * of an embedded view. This is used for instance in the dashboard view in
     * enterprise where there is no GroupBy menu in the search view because it
     * would not make sense to have one at the global level.
     * This function is called by renderButtons when the parameter
     * 'this.isEmbedded' is set to true.
     *
     * private
     * @param {jQuery} $node
     * @param {Object} groupableFields
     */
    _addGroupByMenu: function ($node, groupableFields) {
        this.sortedFieldNames = _.sortBy(Object.keys(groupableFields), function (fieldName) {
            return groupableFields[fieldName].string;
        });
        this.groupableFields = groupableFields;
        var groupBys = this._getGroupBys(this.model.get().groupBy);
        this.groupByMenu = new GroupByMenu(this, groupBys, this.groupableFields);
        this.groupByMenu.insertAfter($node.find('div:first'));
    },
    /**
     * This method puts the active groupBys in a convenient form.
     *
     * @private
     * @param {string[]} activeGroupBys
     * returns {string[]} groupBysNormalized
     */
    _normalizeActiveGroupBys: function (activeGroupBys) {
        var groupBysNormalized = activeGroupBys.map(function (groupBy) {
            return {fieldName: groupBy.split(':')[0], interval: groupBy.split(':')[1] || false};
        });
        return groupBysNormalized;
    },
    /**
     * This method has to be implemented by the view controller that needs to
     * interpret the click in an appropriate manner.
     *
     * @private
     * @param {string[]} groupBys
     */
    _setGroupby: function (groupBys) {},
    /**
     * Return the list of groupBys in a form suitable for the groupByMenu. We do
     * this each time because we want to be synchronized with the view model.
     *
     * @private
     * @param {string[]} activeGroupBys
     * returns {Object[]} groupBys
     */
    _getGroupBys: function (activeGroupBys) {
        var self = this;
        var groupBys = [];
        var groupBysNormalized = this._normalizeActiveGroupBys(activeGroupBys);
        this.sortedFieldNames.forEach(function (fieldName) {
            var field = self.groupableFields[fieldName];
            var groupByActivity = _.findWhere(groupBysNormalized, {fieldName: fieldName});
            var groupBy = {
                id: fieldName,
                isActive: groupByActivity ? true : false,
                description: field.string,
            };
            if (_.contains(['date', 'datetime'], field.type)) {
                groupBy.hasOptions = true;
                groupBy.options = controlPanelViewParameters.INTERVAL_OPTIONS;
                groupBy.currentOptionId = groupByActivity && groupByActivity.interval ?
                                            groupByActivity.interval :
                                            false;
            }
            groupBys.push(groupBy);
        });
        return groupBys;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onItemOptionClicked: function (ev) {
        var fieldName = ev.data.id;
        var optionId = ev.data.optionId;
        var activeGroupBys = this.model.get().groupBy;
        var currentOptionId = activeGroupBys.reduce(
            function (optionId, groupby) {
                if (groupby.split(':')[0] === fieldName){
                    optionId = groupby.split(':')[1] || controlPanelViewParameters.DEFAULT_INTERVAL;
                }
                return optionId;
            },
            false
        );
        var groupByFieldNames = _.map(activeGroupBys, function (groupby) {
            return groupby.split(':')[0];
        });
        var indexOfGroupby = groupByFieldNames.indexOf(fieldName);
        if (indexOfGroupby === -1) {
            activeGroupBys.push(fieldName + ':' + optionId);
        } else if (currentOptionId === optionId) {
            activeGroupBys.splice(indexOfGroupby, 1);
        } else {
            activeGroupBys.splice(indexOfGroupby, 1, fieldName + ':' + optionId);
        }
        this._setGroupby(activeGroupBys);
        this.groupByMenu.update(this._getGroupBys(activeGroupBys));
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onMenuItemClicked: function (ev) {
        var fieldName = ev.data.id;
        var activeGroupBys = this.model.get().groupBy;
        var groupByFieldNames = _.map(activeGroupBys, function (groupby) {
            return groupby.split(':')[0];
        });
        var indexOfGroupby = groupByFieldNames.indexOf(fieldName);
        if (indexOfGroupby === -1) {
            activeGroupBys.push(fieldName);
        } else {
            activeGroupBys.splice(indexOfGroupby, 1);
        }
        this._setGroupby(activeGroupBys);
        this.groupByMenu.update(this._getGroupBys(activeGroupBys));
    },
};

return GroupByMenuMixin;

});
