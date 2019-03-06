 odoo.define('web.SearchViewMobile', function (require) {
"use strict";

var config = require('web.config');
var SearchView = require('web.SearchView');

if (!config.device.isMobile) {
    return;
}

SearchView.include({
    template:'SearchViewMobile',
    events:_.extend({}, SearchView.prototype.events, {
        'click .o_mobile_search_close, .o_mobile_search_show_result, .o_enable_searchview': '_toggleMobileSearchView',
        'click': '_onOpenMobileSearchView',
        'click .o_mobile_search_clear_facets': '_onEmptyAll',
        'show.bs.dropdown .o_mobile_search_filter .o_dropdown': '_onDropdownToggle',
        'hide.bs.dropdown .o_mobile_search_filter .o_dropdown': '_onDropdownToggle',
    }),

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    renderFacets: function () {
        this._super.apply(this, arguments);
        this.$('.o_mobile_search_clear_facets')
            .toggleClass('o_hidden', !this.query.length);
    },
    /**
     * @override
     */
    toggle_visibility: function (is_visible) {
        // Do not do anything, toggling visibility of searchview is handled
        // explicitly for mobile
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getButtonsElement: function () {
        return this.$('.o_mobile_search_filter');
    },
    /**
     * Toggle mobile search view screen
     *
     * @private
     */
    _toggleMobileSearchView: function () {
        this.$('.o_enable_searchview').toggleClass('btn-secondary', !!this.query.length);
        this.$('.o_mobile_search').toggleClass('o_hidden');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Toggle the little arrow in main buttons
     *
     * @private
     * @param {BootstrapEvent} ev
     */
    _onDropdownToggle: function (ev) {
        $(ev.currentTarget).find('.fa-chevron-right').toggleClass('fa-chevron-down');
    },
    /**
     * Clears all filters from the search view
     *
     * @private
     * @param {MouseEvent} event
     */
    _onEmptyAll: function () {
        this.query.reset();
    },
    /**
     * Open the mobile search view screen
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onOpenMobileSearchView: function (ev) {
        if (ev.target === this.el) {
            this._toggleMobileSearchView();
        }
    },
});

});