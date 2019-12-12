odoo.define('web.Menu', function (require) {
"use strict";

const { Component } = owl;
const domUtils = require('web.dom');
const SystrayMenu = require('web.SystrayMenu');

class Menu extends Component {
    constructor() {
        super(...arguments);
        this.menus = this.props.menus;
        this.systrayMenu = owl.hooks.useRef('systrayMenu');
        this.menuBrand = owl.hooks.useRef('menuBrand');
        this.menuSections = owl.hooks.useRef('menuSections');
    }
    mounted() {
        this.$menu_apps = $(this.el.getElementsByClassName('o_menu_apps')[0]);
        domUtils.initAutoMoreMenu($(this.menuSections.el), {
            maxWidth: () => {
                return (
                    this.el.offsetWidth -
                    (
                        this.$menu_apps.outerWidth(true) +
                        $(this.menuBrand.el).outerWidth(true) +
                        $(this.systrayMenu.el).outerWidth(true)
                    )
                );
            },
            sizeClass: 'SM',
        });
    }
    patched() {
        this.env.bus.trigger('resize');
    }
    get apps() {
        return this.menus.root.children.map(childID => this.menus[childID]);
    }
    get currentApp() {
        const currentAppID = this.props.menuID && this.menus[this.props.menuID].appID;
        return this.menus[currentAppID];
    }
    shouldUpdate(nextProps) {
        return nextProps.menuID && nextProps.menuID !== this.props.menuID;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onMouseOverMenu(ev) {
        // TODO: check if necessary
        if (this.env.device.isMobile) {
            return;
        }
        const menuShown = this.el.querySelector('.dropdown-menu.show');
        const target = ev.target;
        if (target.matches('[data-toggle="dropdown"]') && menuShown) {
            const toggleMenuShown = menuShown.parentNode.querySelector('[data-toggle="dropdown"]');
            if (toggleMenuShown !== target) {
                $(toggleMenuShown).dropdown('toggle');
                $(target).dropdown('toggle');
            }
        }
    }
}
Menu.components = { SystrayMenu };
Menu.template = 'web.Menu';

return Menu;
});
