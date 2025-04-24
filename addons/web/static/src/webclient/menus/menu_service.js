import { session } from "@web/session";
import { browser } from "../../core/browser/browser";
import { registry } from "../../core/registry";

export const menuService = {
    dependencies: ["action", "orm"],
    async start(env, { orm }) {
        let currentAppId;
        let menusData = {};

        const storedMenus = browser.localStorage.getItem("webclient_menus");
        const storedMenusVersion = browser.localStorage.getItem("webclient_menus_version");

        if (odoo.loadMenus) {
            if (storedMenus && storedMenusVersion === session.registry_hash) {
                orm.call("ir.ui.menu", "load_web_menus", [!!odoo.debug]).then((res) => {
                    const fetchedMenus = JSON.stringify(res);
                    if (fetchedMenus !== storedMenus) {
                        browser.localStorage.setItem("webclient_menus", fetchedMenus);
                        menusData = res;
                        env.bus.trigger("MENUS:APP-CHANGED");
                    }
                });
                menusData = JSON.parse(storedMenus);
            } else {
                menusData = await orm.call("ir.ui.menu", "load_web_menus", [!!odoo.debug]);
                browser.localStorage.setItem("webclient_menus_version", session.registry_hash);
                browser.localStorage.setItem("webclient_menus", JSON.stringify(menusData));
            }
        }

        function _getMenu(menuId) {
            return menusData[menuId];
        }
        function setCurrentMenu(menu) {
            menu = typeof menu === "number" ? _getMenu(menu) : menu;
            if (menu && menu.appID !== currentAppId) {
                currentAppId = menu.appID;
                browser.sessionStorage.setItem("menu_id", currentAppId);
                env.bus.trigger("MENUS:APP-CHANGED");
            }
        }

        return {
            getAll() {
                return Object.values(menusData);
            },
            getApps() {
                return this.getMenu("root").children.map((mid) => this.getMenu(mid));
            },
            getMenu: _getMenu,
            getCurrentApp() {
                if (!currentAppId) {
                    return;
                }
                return this.getMenu(currentAppId);
            },
            getMenuAsTree(menuID) {
                const menu = this.getMenu(menuID);
                if (!menu.childrenTree) {
                    menu.childrenTree = menu.children.map((mid) => this.getMenuAsTree(mid));
                }
                return menu;
            },
            async selectMenu(menu) {
                menu = typeof menu === "number" ? this.getMenu(menu) : menu;
                if (!menu.actionID) {
                    return;
                }
                await env.services.action.doAction(menu.actionID, {
                    clearBreadcrumbs: true,
                    onActionReady: () => {
                        setCurrentMenu(menu);
                    },
                });
            },
            setCurrentMenu,
            async reload() {
                if (odoo.loadMenus) {
                    menusData = await orm.call("ir.ui.menu", "load_web_menus", [!!odoo.debug]);
                    browser.localStorage.setItem("webclient_menus_version", session.registry_hash);
                    browser.localStorage.setItem("webclient_menus", JSON.stringify(menusData));
                    env.bus.trigger("MENUS:APP-CHANGED");
                }
            },
        };
    },
};

registry.category("services").add("menu", menuService);
