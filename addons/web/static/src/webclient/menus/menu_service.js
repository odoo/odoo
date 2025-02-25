import { browser } from "../../core/browser/browser";
import { registry } from "../../core/registry";
import { session } from "@web/session";
import { deepCopy, deepEqual } from "@web/core/utils/objects";

const loadMenusUrl = `/web/webclient/load_menus`;

function makeFetchLoadMenus() {
    const cacheHashes = session.cache_hashes;
    let loadMenusHash = cacheHashes.load_menus || new Date().getTime().toString();
    return async function fetchLoadMenus(reload) {
        if (reload) {
            loadMenusHash = new Date().getTime().toString();
        } else if (odoo.loadMenusPromise) {
            return odoo.loadMenusPromise;
        }
        const res = await browser.fetch(`${loadMenusUrl}/${loadMenusHash}`);
        if (!res.ok) {
            throw new Error("Error while fetching menus");
        }
        return res.json();
    };
}

function makeMenus(env, menusData, fetchLoadMenus) {
    let currentAppId;
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
            if (fetchLoadMenus) {
                menusData = await fetchLoadMenus(true);
                env.bus.trigger("MENUS:APP-CHANGED");
            }
        },
    };
}

export const menuService = {
    dependencies: ["action"],
    async start(env) {
        const fetchLoadMenus = makeFetchLoadMenus();
        const storageMenus = JSON.parse(browser.localStorage.getItem("webclient_menus_data"));
        const storageMenusVersion = browser.localStorage.getItem("webclient_menus_version");
        if (storageMenus && storageMenusVersion === odoo.info.server_version) {
            const fetchLoadMenusPromise = fetchLoadMenus();
            fetchLoadMenusPromise.then((res) => {
                if (!deepEqual(res, storageMenus)) {
                    browser.localStorage.setItem("webclient_menus", JSON.stringify(res));
                    env.bus.trigger("MENUS:APP-CHANGED");
                }
            });
            // The deepCopy is to be sure to compare non modified on the localStorage;
            return makeMenus(env, deepCopy(storageMenus), fetchLoadMenus);
        }
        const menusData = await fetchLoadMenus();
        browser.localStorage.setItem("webclient_menus_version", odoo.info.server_version);
        browser.localStorage.setItem("webclient_menus_data", JSON.stringify(menusData));
        return makeMenus(env, menusData, fetchLoadMenus);
    },
};

registry.category("services").add("menu", menuService);
