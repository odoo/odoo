odoo.define('website.ControlPanelRenderer', function (require) {
"use strict";

var WebsiteMenu = require('website.WebsiteMenu');
var controlPanelRenderer = require('web.ControlPanelRenderer');

var websiteControlPanelRenderer = controlPanelRenderer.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {string} menuType
     */
    _getMenuItems: function (menuType) {
        var menuItems = this._super.apply(this, arguments);
        if (menuType === 'website') {
            menuItems = this.state.websites;
        }
        return menuItems;
    },
    /**
     * @override
     */
    _renderSearchBar: function () {
        var def = this._super.apply(this, arguments);
        this.searchBarElements.websites = this.state.websites;
        return def;
    },
    /**
     * @override
     * @param {string} menuType
     */
    _setupMenu: function (menuType) {
        var Menu;
        var menu;
        if (menuType === 'website') {
            Menu = WebsiteMenu;
            menu = new Menu(this, this._getMenuItems(menuType), this.state.fields);
            this.subMenus[menuType] = menu;
            return menu.appendTo(this.$subMenus);
        }
        return this._super.apply(this, arguments);
    },
});

return websiteControlPanelRenderer;

});
