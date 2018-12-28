 odoo.define('web.MobileControlPanelRenderer', function (require) {
"use strict";

var config = require('web.config');
var ControlPanelRenderer = require('web.ControlPanelRenderer');

if (!config.device.isMobile) {
    return;
}

ControlPanelRenderer.include({
    template:'MobileControlPanel',
    events:_.extend({}, ControlPanelRenderer.prototype.events, {
        'click .o_mobile_search_close, .o_mobile_search_show_result, .o_enable_searchview': '_toggleMobileSearchView',
        'click': '_onOpenMobileSearchView',
        'click .o_mobile_search_clear_facets': '_onEmptyAll',
        'show.bs.dropdown .o_mobile_search_filter .o_dropdown': '_onDropdownToggle',
        'hide.bs.dropdown .o_mobile_search_filter .o_dropdown': '_onDropdownToggle',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Overridden to correctly place submenu inside the mobile section.
     *
     * @private
     * @override
     */
    _getSubMenusPlace: function () {
        return this.$('.o_mobile_search_filter');
    },
    /**
     * @private
     * @override
     */
    _render: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$('.o_mobile_search_clear_facets')
                .toggleClass('o_hidden', !self.state.query.length);
        });
    },
    /**
     * @private
     * @override
     */
    _renderSearchBar: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.searchBar.$el.detach().insertAfter(self.$('.o_mobile_search_header'));
        });
    },
    /**
     * Toggles mobile search view screen.
     *
     * @private
     */
    _toggleMobileSearchView: function () {
        this.$('.o_enable_searchview').toggleClass('btn-secondary', !!this.state.query.length);
        this.$('.o_mobile_search').toggleClass('o_hidden');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Toggles the little arrow in main buttons.
     *
     * @private
     * @param {BootstrapEvent} ev
     */
    _onDropdownToggle: function (ev) {
        $(ev.currentTarget).find('.fa-chevron-right').toggleClass('fa-chevron-down');
    },
    /**
     * Clears all filters from the search view.
     *
     * @private
     */
    _onEmptyAll: function () {
        this.trigger_up('search_bar_cleared');
    },
    /**
     * Opens the mobile search view screen.
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
