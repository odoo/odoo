import { browser } from "../../core/browser/browser";
import { registry } from "../../core/registry";
import { deepCopy, deepEqual } from "@web/core/utils/objects";

const loadMenusUrl = `/web/webclient/load_menus`;
const loadMenusHash = new Date().getTime().toString();

function makeFetchLoadMenus() {
    return async function fetchLoadMenus(reload) {
        if (!reload && odoo.loadMenusPromise) {
            return odoo.loadMenusPromise;
        }
        const res = await browser.fetch(`${loadMenusUrl}/${loadMenusHash}`);
        if (!res.ok) {
            throw new Error("Error while fetching menus");
        }
        return res.json();
    };
}

export const menuService = {
    dependencies: ["action"],
    async start(env) {
        let currentAppId;
        let menusData;

        const fetchLoadMenus = makeFetchLoadMenus();
        const storageMenus = JSON.parse(browser.localStorage.getItem("webclient_menus_data"));
        const storageMenusVersion = browser.localStorage.getItem("webclient_menus_version");
        if (storageMenus && storageMenusVersion === odoo.info.server_version) {
            const fetchLoadMenusPromise = fetchLoadMenus();
            fetchLoadMenusPromise.then((res) => {
                if (!deepEqual(res, storageMenus)) {
                    browser.localStorage.setItem("webclient_menus_data", JSON.stringify(res));
                    menusData = res;
                    env.bus.trigger("MENUS:APP-CHANGED");
                }
            });
            // deepCopy the storageMenus, to keep it unmodified for future comparaison with the result of the fetch.
            menusData = deepCopy(storageMenus);
        } else {
            menusData = await fetchLoadMenus();
            browser.localStorage.setItem("webclient_menus_version", odoo.info.server_version);
            browser.localStorage.setItem("webclient_menus_data", JSON.stringify(menusData));
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
                if (fetchLoadMenus) {
                    menusData = await fetchLoadMenus(true);
                    env.bus.trigger("MENUS:APP-CHANGED");
                }
            },
        };
    },
};

registry.category("services").add("menu", menuService);
