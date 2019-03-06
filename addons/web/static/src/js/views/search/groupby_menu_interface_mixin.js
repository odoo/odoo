odoo.define('web.GroupByMenuInterfaceMixin', function (require) {
"use strict";

var GroupByMenu = require('web.GroupByMenu');

/**
 * The aim of this mixin is to facilitate the interaction between
 * a view controller and a dropdown menu with its control panel
 * TO DO: the pivot subview has two types of groupbys so that it will not
 * understand the current implementation of this mixin
 *
 * @mixin
 * @name GroupByMenuInterfaceMixin
 */
var GroupByMenuInterfaceMixin = {

    init: function () {
        this.custom_events = _.extend({}, this.custom_events, {
                menu_item_toggled: '_onMenuItemToggled',
                item_option_changed : '_onItemOptionChanged',});
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * this function instantiate a widget GroupByMenu and
     * incorporate it to the control panel of the graph view.
     * This is used for instance in the dashboard view in enterprise
     * where there is no Group by menu in the search view because it
     * would not make sense to have one at the global level.
     * this function is called by renderButtons when the parameter
     * 'this.isEmbedded' is set to true.
     *
     * private
     * @param {jQuery} $node
     */
    _addGroupByMenu: function ($node, groupableFields) {
        var groupbys = [];
        var activeGroupbys = [];
        _.each(this.model.get().groupedBy, function (groupby) {
            activeGroupbys.push({fieldName: groupby.split(':')[0], interval: groupby.split(':')[1] || false});
        });
        var groupId = '__group__1';
        _.each(groupableFields, function (field, fieldName) {
            var groupby = _.findWhere(activeGroupbys, {fieldName: fieldName});
            groupbys.push({
                isActive: groupby ? true : false,
                description: field.string,
                itemId: fieldName,
                fieldName: fieldName,
                groupId: groupId,
                defaultOptionId: groupby ? groupby.interval : false,
            });
        });
        groupbys = _.sortBy(groupbys, 'description');
        var groupByMenu = new GroupByMenu(this, groupbys, groupableFields, {headerStyle: 'primary'});
        groupByMenu.insertAfter($node.find('div:first'));
    },

    /**
     * This method has to be implemented by the view controller
     * that needs to interpret the click in an appropriate
     * manner
     *
     * @private
     * @param {string[]} groupbys
     */
    _setGroupby: function (groupbys) {
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     *
     * @private
     * @param {OdooEvent} ev
     */
     _onItemOptionChanged: function (ev) {
        var fieldName = ev.data.itemId;
        var interval = ev.data.optionId;
        var groupbys = this.model.get().groupedBy;
        var groupbysNormalized = _.map(groupbys, function (groupby) {
            return groupby.split(':')[0];
        });
        var indexOfGroupby = groupbysNormalized.indexOf(fieldName);
        groupbys.splice(indexOfGroupby, 1, fieldName + ':' + interval);
        this._setGroupby(groupbys);
     },
    /**
     *
     * @private
     * @param {OdooEvent} ev
     */
     _onMenuItemToggled: function (ev) {
        var fieldName = ev.data.itemId;
        var interval = ev.data.optionId;
        var groupbys = this.model.get().groupedBy;
        var groupbysNormalized = _.map(groupbys, function (groupby) {
            return groupby.split(':')[0];
        });
        var indexOfGroupby = groupbysNormalized.indexOf(fieldName);
        if (indexOfGroupby === -1) {
            groupbys.push(fieldName + (interval ? (':' + interval) : ''));
        } else {
            groupbys.splice(indexOfGroupby, 1);
        }
        this._setGroupby(groupbys);
     },
};

return GroupByMenuInterfaceMixin;

});