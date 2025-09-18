// @ts-check

/** @module @web/webclient/menus/menu_service - Service that loads, caches, and navigates the Odoo menu tree */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

const loadMenusUrl = `/web/webclient/load_menus`;

/**
 * Service that loads, caches, and navigates the Odoo menu tree.
 *
 * Fetches menus from `/web/webclient/load_menus`, stores them in localStorage
 * for fast startup, and exposes methods to query apps, sub-menus, and trigger
 * navigation via the action service.
 */
export const menuService = {
    dependencies: ["action"],
    async start(env) {
        let currentAppId;
        let menusData;

        const fetchMenus = async (reload) => {
            if (!reload && /** @type {any} */ (odoo).loadMenusPromise) {
                return /** @type {any} */ (odoo).loadMenusPromise;
            }
            const res = await browser.fetch(loadMenusUrl, {
                cache: "no-store",
            });
            if (!res.ok) {
                throw new Error("Error while fetching menus");
            }
            return res.json();
        };
        const storedMenus = browser.localStorage.getItem("webclient_menus");
        const storedMenusVersion = browser.localStorage.getItem(
            "webclient_menus_version",
        );

        if (storedMenus && storedMenusVersion === session.registry_hash) {
            fetchMenus().then((res) => {
                if (res) {
                    const fetchedMenus = JSON.stringify(res);
                    if (fetchedMenus !== storedMenus) {
                        try {
                            browser.localStorage.setItem(
                                "webclient_menus",
                                fetchedMenus,
                            );
                        } catch (error) {
                            console.error(
                                "Error while storing menus in localStorage",
                                error,
                            );
                        }
                        menusData = res;
                        env.bus.trigger("MENUS:APP-CHANGED");
                    }
                }
            });
            menusData = JSON.parse(storedMenus);
        } else {
            menusData = await fetchMenus();
            if (menusData) {
                try {
                    browser.localStorage.setItem(
                        "webclient_menus_version",
                        session.registry_hash,
                    );
                    browser.localStorage.setItem(
                        "webclient_menus",
                        JSON.stringify(menusData),
                    );
                } catch (error) {
                    console.error("Error while storing menus in localStorage", error);
                }
            }
        }

        /** @param {number|string} menuId */
        function _getMenu(menuId) {
            return menusData[menuId];
        }
        /** @param {Object|number} menu - menu descriptor or menu ID */
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
                    menu.childrenTree = menu.children.map((mid) =>
                        this.getMenuAsTree(mid),
                    );
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
                if (fetchMenus) {
                    menusData = await fetchMenus(true);
                    env.bus.trigger("MENUS:APP-CHANGED");
                }
            },
        };
    },
};

registry.category("services").add("menu", menuService);
