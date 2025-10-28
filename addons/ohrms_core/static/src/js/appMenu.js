/** @odoo-module */
import { NavBar } from "@web/webclient/navbar/navbar";
import { registry } from "@web/core/registry";
const { fuzzyLookup } = require('@web/core/utils/search');
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { onMounted, Component, useRef, useState } from "@odoo/owl";
const commandProviderRegistry = registry.category("command_provider");
import { patch } from "@web/core/utils/patch";
patch(NavBar.prototype, {
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * @override
     */
     setup() {
        super.setup();
        this.search_input = useRef("search-input")
        this._search_def = new $.Deferred();
        let { apps, menuItems } = computeAppsAndMenuItems(this.menuService.getMenuAsTree("root"));
        this._apps = apps;
        this._searchableMenus = menuItems;
        this.state = useState({
            results : [],
        })
    },

        _onMenuClick(ev) {
        ev.preventDefault();
        const liEl = ev.currentTarget.closest("li");
        const menuEl = liEl.querySelector(".dropdown-menu");
        menuEl.classList.toggle("show");
    },

    _closeFullMenu(ev) {
    //while click on the  app icon  this function will close the
    const dropdownMenu = ev.currentTarget.closest(".dropdown-menu");
    if (dropdownMenu) {
        dropdownMenu.classList.remove("show");
    }
    },

     _searchMenusSchedule() {
        $('.search-results').removeClass("o_hidden");
        $('.app-menu').addClass("o_hidden");
        this._search_def.reject();
        this._search_def = $.Deferred();
        setTimeout(this._search_def.resolve.bind(this._search_def), 50);
        this._search_def.done(this._searchMenus.bind(this));
    },
    _searchMenus() {
        var query = this.search_input.el.value
        if (query === "") {
            $('.search-container').removeClass("has-results");
            $('.app-menu').removeClass("o_hidden");
            $('.search-results').empty();
            return;
        }
        var results = [];
        fuzzyLookup(query, this._apps, (menu) => menu.label)
        .forEach((menu) => {
            results.push({
                category: "apps",
                name: menu.label,
                actionID: menu.actionID,
                id: menu.id,
                webIconData: menu.webIconData.split(',')[1],
            });
        });
        fuzzyLookup(query, this._searchableMenus, (menu) =>
            (menu.parents + " / " + menu.label).split("/").reverse().join("/"))
        .forEach((menu) => {
            results.push({
                category: "menu_items",
                name: menu.parents + " / " + menu.label,
                actionID: menu.actionID,
                id: menu.id,
            });
        });
        $('.search-container').toggleClass(
            "has-results",
            Boolean(results.length)
        );
        this.state.results = results
    }
});
