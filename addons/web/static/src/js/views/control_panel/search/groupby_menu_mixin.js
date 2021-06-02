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
     * @param {Promise}
     */
    _addGroupByMenu: function ($node, groupableFields) {
        this.sortedFieldNames = Object.keys(groupableFields).sort();
        this.groupableFields = groupableFields;
        const groupBys = this._getGroupBys(this.model.get().groupBy);
        this.groupByMenu = new GroupByMenu(this, groupBys, this.groupableFields, {noSymbol: true});
        return this.groupByMenu.insertAfter($node.find('div:first'));
    },
    /**
     * This method puts the active groupBys in a convenient form.
     *
     * @private
     * @param {string[]} activeGroupBys
     * returns {Object[]} groupBysNormalized
     */
    _normalizeActiveGroupBys: function (activeGroupBys) {
        return activeGroupBys.map(gb => {
            const fieldName = gb.split(':')[0];
            const field = this.groupableFields[fieldName];
            const ngb = {fieldName: fieldName};
            if (_.contains(['date', 'datetime'], field.type)) {
                ngb.interval = gb.split(':')[1] || controlPanelViewParameters.DEFAULT_INTERVAL;
            }
            return ngb;
        });
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
        const groupBysNormalized = this._normalizeActiveGroupBys(activeGroupBys);
        return this.sortedFieldNames.map(fieldName => {
            const field = this.groupableFields[fieldName];
            const groupByActivity = groupBysNormalized.filter(gb => (gb.fieldName === fieldName));
            const groupBy = {
                id: fieldName,
                isActive: groupByActivity.length ? true : false,
                description: field.string,
            };
            if (_.contains(['date', 'datetime'], field.type)) {
                groupBy.hasOptions = true;
                groupBy.options = controlPanelViewParameters.INTERVAL_OPTIONS;
                groupBy.currentOptionIds = groupByActivity.length ?
                                            new Set(groupByActivity.map(gb => gb.interval)) :
                                            new Set([]);
            }
            return groupBy;
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onItemOptionClicked: function (ev) {
        const fieldName = ev.data.id;
        const optionId = ev.data.optionId;
        const activeGroupBys = this.model.get().groupBy;
        const groupBysNormalized = this._normalizeActiveGroupBys(activeGroupBys);
        const index = groupBysNormalized.findIndex(ngb =>
            ngb.fieldName === fieldName && ngb.interval === optionId);
        if (index === -1) {
            activeGroupBys.push(fieldName + ':' + optionId);
        } else {
            activeGroupBys.splice(index, 1);
        }
        this._setGroupby(activeGroupBys);
        this.groupByMenu.update(this._getGroupBys(activeGroupBys));
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onMenuItemClicked: function (ev) {
        const fieldName = ev.data.id;
        const activeGroupBys = this.model.get().groupBy;
        const groupByFieldNames = activeGroupBys.map(gb => gb.split(':')[0]);
        const indexOfGroupby = groupByFieldNames.indexOf(fieldName);
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
