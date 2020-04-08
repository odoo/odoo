odoo.define('web.Menu', function (require) {
"use strict";

const { Component } = owl;
const domUtils = require('web.dom');
const SystrayMenu = require('web.SystrayMenu');

class Menu extends Component {
    constructor() {
        super(...arguments);
        this.systrayMenu = owl.hooks.useRef('systrayMenu');
        this.menuBrand = owl.hooks.useRef('menuBrand');
        this.menuSections = owl.hooks.useRef('menuSections');
    }
    get menuAppsEl() {
        if (!this.el) {return null;}
        return this.el.getElementsByClassName('o_menu_apps')[0];
    }
    mounted() {
        this._initAutoMoreMenu();
    }
    patched() {
        this._initAutoMoreMenu();
    }
    get apps() {
        return this.props.menus.root.children.map(childID => this.props.menus[childID]);
    }
    get currentApp() {
        const currentAppID = this.props.menuID && this.props.menus[this.props.menuID].appID;
        return this.props.menus[currentAppID];
    }
    shouldUpdate(nextProps) {
        return nextProps.menuID !== this.props.menuID;
    }
    _initAutoMoreMenu() {
        let reInit = false;
        const candidateAutoMore = this.menuSections.el;
        if (candidateAutoMore) {
            if (!this.autoMoreMenu || candidateAutoMore !== this.autoMoreMenu) {
                this.autoMoreMenu = candidateAutoMore;
                reInit = true;
            }
        }
        if (reInit) {
            domUtils.initAutoMoreMenu($(this.autoMoreMenu), {
                maxWidth: this._getMaxWidth.bind(this),
                sizeClass: 'SM',
            });
        } else if (this.autoMoreMenu) {
            this.env.bus.trigger('resize');
        }
    }
    _getMaxWidth() {
        return (
            this.el.offsetWidth -
            (
                ($(this.menuAppsEl).outerWidth(true) || 0) +
                ($(this.menuBrand.el).outerWidth(true) || 0) +
                ($(this.systrayMenu.el).outerWidth(true) || 0)
            )
        );
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
