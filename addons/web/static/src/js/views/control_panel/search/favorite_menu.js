odoo.define('web.FavoriteMenu', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var DropdownMenu = require('web.DropdownMenu');
var favorites_submenus_registry = require('web.favorites_submenus_registry');

var _t = core._t;

var FavoriteMenu = DropdownMenu.extend({
    custom_events: _.extend({}, DropdownMenu.prototype.custom_events, {
        favorite_submenu_toggled: '_onSubMenuToggled',
    }),
    /**
     * @override
     * @param {Object} action
     */
    init: function (parent, favorites, action) {
        this._super(parent, favorites);
        this.action = action;
        this.isMobile = config.device.isMobile;
        this.dropdownCategory = 'favorite';
        this.dropdownTitle = _t('Favorites');
        this.dropdownIcon = 'fa fa-star';
        this.dropdownSymbol = this.isMobile ? 'fa fa-chevron-right float-right mt4' : false;
        this.dropdownStyle.mainButton.class = 'o_favorites_menu_button ' +
                                                this.dropdownStyle.mainButton.class;

    },
    /**
     * Render the template used to register a new favorite and append it
     * to the basic dropdown menu.
     *
     * @override
     */
    start: function () {
        var self = this;
        var params = {
            favorites: this.items,
            action: this.action,
        };
        var superProm = this._super.apply(this, arguments);
        this.$menu.addClass('o_favorites_menu');
        this.subMenus = [];
        favorites_submenus_registry.values().forEach(function (SubMenu) {
            var subMenu = new SubMenu(self, params);
            subMenu.appendTo(self.$menu);
            self.subMenus.push(subMenu);
        });
        return superProm;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    update: function (items) {
        this._super.apply(this, arguments);
        _.invoke(this.subMenus, 'update', { favorites: this.items });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
     _closeSubMenus: function () {
        _.invoke(this.subMenus, 'closeMenu');
     },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _onBootstrapClose: function () {
        this._super.apply(this, arguments);
        this._closeSubMenus();
    },
    /**
     * Reacts to a submenu being toggled
     *
     * When a submenu is toggled, it has changed the position
     * and size of the Favorite's dropdown. This method
     * repositions the current dropdown
     *
     * @private
     * @param {OdooEvent} ev
     *
     */
    _onSubMenuToggled: function (ev) {
        ev.stopPropagation();
        this.$dropdownReference.dropdown('update');
    },
    /**
     * @override
     * @private
     * @param {MouseEvent} event
     */
    _onTrashButtonClick: function (event) {
        event.preventDefault();
        event.stopPropagation();
        var self = this;
        var id = $(event.currentTarget).data('id');
        var favorite = this.items.find(function (favorite) {
            return favorite.id === id;
        });
        var globalWarning = _t("This filter is global and will be removed for everybody if you continue.");
        var warning = _t("Are you sure that you want to remove this filter?");
        var message = favorite.userId ? warning : globalWarning;

        Dialog.confirm(self, message, {
            title: _t("Warning"),
            confirm_callback: function () {
                self.trigger_up('item_trashed', {id: id});
            },
        });

    },
});

return FavoriteMenu;

});