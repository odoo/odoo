/** @odoo-module */
import { NavBar } from "@web/webclient/navbar/navbar";
import { registry } from "@web/core/registry";
import { fuzzyLookup } from "@web/core/utils/search";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { useService } from "@web/core/utils/hooks";
import { onMounted, useRef, useState} from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

patch(NavBar.prototype, {
    // To modify the Navbar properties and functions.
    setup() {
        super.setup()
        this._search_def = this.createDeferred();
        this.search_container = useRef("search-container");
        this.search_input = useRef("search-input");
        this.search_result = useRef("search-results");
        this.menuService = useService("menu");
        this.app_menu = useRef("app-menu");
        this.sidebar_panel = useRef("sidebar_panel");
        this.app_components = useRef("app_components");
        this.state = useState({...this.state, menus: [], searchQuery: ""})
        let { apps, menuItems } = computeAppsAndMenuItems(this.menuService.getMenuAsTree("root"));
        this._apps = apps;
        this._searchableMenus = menuItems;
        this.fetch_data()
        onMounted(() => {
            this.setClass()
        })
    },
    createDeferred() {
    let deferred = {};

    deferred.promise = new Promise((resolve, reject) => {
        deferred.resolve = resolve;
        deferred.reject = reject;
    });

    return deferred;
},
    async fetch_data() {
        // To fetch colors from database.
        this.orm = useService("orm")
        var result = await this.orm.call("res.config.settings", "config_color_settings", [0])
        if (result.primary_accent !== false){
            document.documentElement.style.setProperty("--primary-accent",result.primary_accent)
        }
        if (result.appbar_color !== false){
            document.documentElement.style.setProperty("--app-bar-accent",result.appbar_color)
        }
        if (result.primary_hover !== false){
            document.documentElement.style.setProperty("--primary-hover",result.primary_hover)
        }
        if (result.full_bg_img !== false) {
            var imageUrl = 'url(data:image/png;base64,' + result.full_bg_img + ')';
            var appComponentsDivs = document.getElementsByClassName('app_components');

            for (var i = 0; i < appComponentsDivs.length; i++) {
                appComponentsDivs[i].style.backgroundImage = imageUrl;
            }
        }
        if (result.appbar_text !== false){
            document.documentElement.style.setProperty("--app-menu-font-color",result.appbar_text)
        }
        if (result.secondary_hover !== false){
            document.documentElement.style.setProperty("--secondary-hover",result.secondary_hover)
        }
        if (result.kanban_bg_color !== false) {
            document.documentElement.style.setProperty("--kanban-bg-color", result.kanban_bg_color)
        }
    },
    setClass() {
        // Set variable for html elements.
        this.$search_container = this.search_container;
        this.$search_input = this.search_input;
        this.$search_results = this.search_result;
        this.$app_menu = this.app_menu;
    },
    _searchMenusSchedule() {
        this.$search_results.el.classList.remove("o_hidden");
        this.$app_menu.el.classList.add("o_hidden");
        this._search_def = this.createDeferred();
        this._searchMenus();
    },
    _searchMenus() {
        // App menu search function
        var query = this.state.searchQuery;
        if (query === "") {
            this.$search_container.el.classList.remove("has-results");
            this.$search_results.el.classList.add("o_hidden")
            this.$app_menu.el.classList.remove("o_hidden");
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
                webIconData: menu.webIconData,
            });
        });
        fuzzyLookup(query, this._searchableMenus, (menu) =>
            (menu.parents + " / " + menu.label).split("/").reverse().join("/")
        ).forEach((menu) => {
            results.push({
                category: "menu_items",
                name: menu.parents + " / " + menu.label,
                actionID: menu.actionID,
                id: menu.id,
            });
        });
        this.state.menus = results
    },
    get menus() {
        return this.state.menus
    },
    handleClick(menu) {
        this.app_components.el.nextSibling.style.display = "block";
        this.app_components.el.style.display = "none";

        this.sidebar_panel.el.style.display = "block";
        this.app_menu.el.classList.remove('o_hidden');

        let children = this.app_components.el.parentElement.children;
        let oNavbar = null;

        for (let i = 0; i < children.length; i++) {
            if (children[i].classList.contains('o_navbar')) {
                oNavbar = children[i];
                break;
            }
        }

        let navChild = oNavbar.children[0].children;
        for (let i = 0; i < navChild.length; i++) {
            if (navChild[i].classList.contains('o_menu_brand')) {
                navChild[i].classList.remove('d-none');
                navChild[i].classList.add('d-block');
            }
            if (navChild[i].classList.contains('o_menu_sections')) {
                navChild[i].classList.remove('d-none');
                navChild[i].classList.add('d-block');
            }
        }
        if (menu) {
            this.menuService.selectMenu(menu.id);
        }
    },
    OnClickMainMenu() {
        // To show search screen
        if (this.app_components.el.style.display === "" || this.app_components.el.style.display === "none" ) {
            let children = this.app_components.el.parentElement.children;
            let oNavbar = null;
            for (let i = 0; i < children.length; i++) {
                if (children[i].classList.contains('o_navbar')) {
                    oNavbar = children[i];
                    break;
                }
            }
            let navChild = oNavbar.children[0].children
            for (let i = 0; i < navChild.length; i++) {
                if (navChild[i].classList.contains('o_menu_brand')) {
                    navChild[i].classList.add('d-none')
                }
                if (navChild[i].classList.contains('o_menu_sections')) {
                    navChild[i].classList.add('d-none')
                }
            }
            this.app_components.el.style.transition = "opacity 0.25s"
            this.app_components.el.style.opacity="1"
            this.app_components.el.style.display = "block"
            this.app_components.el.nextSibling.style.display = "none"
            this.sidebar_panel.el.style.display = "none"
        } else {
            this.app_components.el.style.transition = "opacity 0.05s";
            this.app_components.el.style.opacity = "0";
            setTimeout(() => {
                this.app_components.el.style.display = "none";
            }, 50);
            this.app_components.el.nextSibling.style.display = "block"
            this.sidebar_panel.el.style.display = "block"
            let children = this.app_components.el.parentElement.children;
            let oNavbar = null;
            for (let i = 0; i < children.length; i++) {
                if (children[i].classList.contains('o_navbar')) {
                    oNavbar = children[i];
                    break;
                }
            }
            let navChild = oNavbar.children[0].children
            for (let i = 0; i < navChild.length; i++) {
                if (navChild[i].classList.contains('o_menu_brand')) {
                    navChild[i].classList.remove('d-none')
                }
                if (navChild[i].classList.contains('o_menu_sections')) {
                    navChild[i].classList.remove('d-none')
                }
            }
        }
    },
    onNavBarDropdownItemSelection(app) {
        // To go to app menu
        this.app_components.el.style.display = "none";
        this.app_components.el.nextSibling.style.display = "block"
        this.sidebar_panel.el.style.display = "block"
        let children = this.app_components.el.parentElement.children;
            let oNavbar = null;
            for (let i = 0; i < children.length; i++) {
                if (children[i].classList.contains('o_navbar')) {
                    oNavbar = children[i];
                    break;
                }
            }
            let navChild = oNavbar.children[0].children
            for (let i = 0; i < navChild.length; i++) {
                if (navChild[i].classList.contains('o_menu_brand')) {
                    navChild[i].classList.add('d-flex')
                    navChild[i].classList.remove('d-none')
                }
                if (navChild[i].classList.contains('o_menu_sections')) {
                    navChild[i].classList.add('d-flex')
                    navChild[i].classList.remove('d-none')
                }
            }
        if (app) {
            this.menuService.selectMenu(app);
        }
    },
    refreshNavBar() {
        // Find the navbar element
        let children = this.app_components.el.parentElement.children;
        let oNavbar = null;

        // Locate the navbar component
        for (let i = 0; i < children.length; i++) {
            if (children[i].classList.contains('o_navbar')) {
                oNavbar = children[i];
                break;
            }
        }

        if (oNavbar) {
            let navChild = oNavbar.children[0].children;
            // Ensure the navbar sections are displayed correctly
            for (let i = 0; i < navChild.length; i++) {
                if (navChild[i].classList.contains('o_menu_brand')) {
                    navChild[i].classList.remove('d-none');
                    navChild[i].classList.add('d-block');
                }
                if (navChild[i].classList.contains('o_menu_sections')) {
                    navChild[i].classList.remove('d-none');
                    navChild[i].classList.add('d-block');
                }
            }
        }
    }
})
