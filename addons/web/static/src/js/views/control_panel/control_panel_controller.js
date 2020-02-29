odoo.define('web.ControlPanelController', function (require) {
"use strict";

var mvc = require('web.mvc');

var ControlPanelController = mvc.Controller.extend({
    className: 'o_cp_controller',
    custom_events: {
        facet_removed: '_onFacetRemoved',
        get_search_query: '_onGetSearchQuery',
        item_option_clicked: '_onItemOptionClicked',
        item_trashed: '_onItemTrashed',
        menu_item_clicked: '_onMenuItemClicked',
        new_favorite: '_onNewFavorite',
        new_filters: '_onNewFilters',
        new_groupBy: '_onNewGroupBy',
        activate_time_range: '_onActivateTimeRange',
        autocompletion_filter: '_onAutoCompletionFilter',
        reload: '_onReload',
        reset: '_onReset',
    },

    /**
     * @override
     * @param {Object} params
     * @param {string} params.modelName
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);

        this.modelName = params.modelName;
    },
    /**
     * Called when the control panel is inserted into the DOM.
     */
    on_attach_callback: function () {
        this.renderer.on_attach_callback();
    },
    /**
     * Called when the control panel is remove form the DOM.
     */
    on_detach_callback: function () {
        this.renderer.on_detach_callback();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @see ControlPanelModel (exportState)
     * @returns {Object}
     */
    exportState: function () {
        return this.model.exportState();
    },
    /**
     * Called by the abstract controller to give focus to the searchbar
     */
    focusSearchBar: function () {
        if (this.renderer.searchBar) {
            this.renderer.searchBar.focus();
        }
    },
    /**
     * Compute the search related values that will be used to fetch data.
     *
     * @returns {Object} object with keys 'context', 'domain', 'groupBy'
     */
    getSearchQuery: function () {
        return this.model.getQuery();
    },
    /**
     * @param {Object} state a ControlPanelModel state
     * @returns {Promise<Object>} the result of `getSearchState`
     */
    importState: function (state) {
        var defs = [];
        this.model.importState(state);
        defs.push(this.getSearchQuery());
        defs.push(this.renderer.updateState(this.model.get()));
        return Promise.all(defs).then(function (defsResults) {
            return defsResults[0];
        });
    },
    /**
     * Called at each switch view. This is required until the control panel is
     * shared between controllers of an action.
     *
     * @param {string} controllerID
     */
    setControllerID: function (controllerID) {
        this.controllerID = controllerID;
    },
    /**
     * Update the content and displays the ControlPanel.
     *
     * @see  ControlPanelRenderer (updateContents)
     * @param {Object} status
     * @param {Object} [options]
     */
    updateContents: function (status, options) {
        this.renderer.updateContents(status, options);
    },
    /**
     * Update the domain of the search view by adding and/or removing filters.
     *
     * @todo: the way it is done could be improved, but the actual state of the
     * searchview doesn't allow to do much better.

     * @param {Object[]} newFilters list of filters to add, described by
     *   objects with keys domain (the domain as an Array), description (the text
     *   to display in the facet) and type with value 'filter'.
     * @param {string[]} filtersToRemove list of filter ids to remove
     *   (previously added ones)
     * @returns {string[]} list of added filters (to pass as filtersToRemove
     *   for a further call to this function)
     */
    updateFilters: function (newFilters, filtersToRemove) {
        var newFilterIDS = this.model.createNewFilters(newFilters);
        this.model.deactivateFilters(filtersToRemove);
        this._reportNewQueryAndRender();
        return newFilterIDS;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {jQuery}
     */
    _getSubMenus: function () {
        return this.renderer.$subMenus;
    },
    /**
     * @private
     * @returns {Promise}
     */
    _reportNewQueryAndRender: function () {
        this.trigger_up('search', this.model.getQuery());
        var state = this.model.get();
        return this.renderer.updateState(state);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onActivateTimeRange: function (ev) {
        ev.stopPropagation();
        this.model.activateTimeRange(
            ev.data.id,
            ev.data.timeRangeId,
            ev.data.comparisonTimeRangeId
        );
        this._reportNewQueryAndRender();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onAutoCompletionFilter: function (ev) {
        ev.stopPropagation();
        this.model.toggleAutoCompletionFilter(ev.data);
        this._reportNewQueryAndRender();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onFacetRemoved: function (ev) {
        ev.stopPropagation();
        var group = ev.data.group || this.renderer.getLastFacet();
        if (group) {
            this.model.deactivateGroup(group.id);
            this._reportNewQueryAndRender();
        }
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onGetSearchQuery: function (ev) {
        ev.stopPropagation();
        var query = this.getSearchQuery();
        ev.data.callback(query);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onItemOptionClicked: function (ev) {
        ev.stopPropagation();
        this.model.toggleFilterWithOptions(ev.data.id, ev.data.optionId);
        this._reportNewQueryAndRender();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onItemTrashed: function (ev) {
        ev.stopPropagation();
        var def = this.model.deleteFilterEverywhere(ev.data.id);
        def.then(this._reportNewQueryAndRender.bind(this));
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onMenuItemClicked: function (ev) {
        ev.stopPropagation();
        this.model.toggleFilter(ev.data.id);
        this._reportNewQueryAndRender();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onNewFavorite: function (ev) {
        ev.stopPropagation();
        var def = this.model.createNewFavorite(ev.data);
        def.then(this._reportNewQueryAndRender.bind(this));
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onNewFilters: function (ev) {
        ev.stopPropagation();
        this.model.createNewFilters(ev.data.filters);
        this._reportNewQueryAndRender();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onNewGroupBy: function (ev) {
        ev.stopPropagation();
        this.model.createNewGroupBy(ev.data);
        this._reportNewQueryAndRender();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onReload: function (ev) {
        ev.stopPropagation();
        this.trigger_up('search', this.model.getQuery());
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onReset: function (ev) {
        ev.stopPropagation();
        var state = this.model.get();
        this.renderer.updateState(state);
    },
});

return ControlPanelController;

});
