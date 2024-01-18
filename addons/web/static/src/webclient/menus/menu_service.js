/** @odoo-module **/

import { browser } from "../../core/browser/browser";
import { registry } from "../../core/registry";
import { session } from "@web/session";
import { router } from "@web/core/browser/router";

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
    function _updateURL(menuId) {
        router.pushState({ menu_id: menuId });
    }
    function _setCurrentMenu(menu, updateURL = true) {
        menu = typeof menu === "number" ? _getMenu(menu) : menu;
        if (menu && menu.appID !== currentAppId) {
            currentAppId = menu.appID;
            env.bus.trigger("MENUS:APP-CHANGED");
            if (updateURL) {
                _updateURL(menu.id);
            }
        }
    }

    function _findActionInMenu(menu, actionID) {
        if (!menu) {
            return;
        }
        if (menu.actionID === actionID) {
            return menu;
        }
        if (!menu.childrenTree) {
            return;
        }
        return _findActionInMenu(menu.childrenTree[0], actionID);
    }

    function _menuRouteToUrl(route) {
        if (route.menu_id) {
            let menu = _getMenu(route.menu_id);
            // Find the first element of the url the app.
            const app = _getMenu(menu.appID);
            let pathname = `/${app.path || app.xmlid}`;
            delete route.menu_id;
            if (menu.id === app.id) {
                menu =
                    _findActionInMenu(menu.childrenTree && menu.childrenTree[0], app.actionID) ??
                    menu;
            }
            // If there is not an action or the action is not the same as the one of the menu,
            // we need to add the action/model to the url.
            if (!route.action || route.action !== menu.actionID) {
                return { pathname, route, continue: true };
            }
            if (menu.id !== app.id) {
                pathname += `/${menu.path || menu.xmlid}`;
            }
            delete route.action;
            delete route.model;
            if (route.view_type && !route.id) {
                pathname += `/${route.view_type}`;
                delete route.view_type;
            } else if (route.id) {
                pathname += `/${route.id}`;
                delete route.view_type;
                delete route.id;
            }
            return { pathname, route };
        }

        return false;
    }

    function _menuGetRoute(splitPath) {
        const state = {};
        const apps = _getMenu("root").children.map((mid) => _getMenu(mid));
        const app = Object.values(apps).find(
            (m) => splitPath[0] === m.path || splitPath[0] === m.xmlid
        );
        if (!app) {
            return false;
        }
        const menu = Object.values(menusData).find(
            (m) => m.appID === app.id && (splitPath[1] === m.path || splitPath[1] === m.xmlid)
        );
        if (!menu) {
            if (app) {
                state.menu_id = app.id;
                return { state, continue: true };
            }
            return false;
        }
        state.menu_id = menu.id;
        if (menu.actionID) {
            state.action = menu.actionID;
        }
        if (splitPath.length === 3) {
            if (isNaN(parseInt(splitPath[2]))) {
                // URL has a view type as last parameter, so it's a multi-record view
                state.view_type = splitPath[2];
            } else {
                // URL has an id as last paremeter, so it's a form view
                state.view_type = "form";
                state.id = parseInt(splitPath[2]);
            }
        }
        return { state };
    }

    registry.category("routeToUrl").add("menuRouteToUrl", _menuRouteToUrl, { sequence: 1 });
    registry.category("getRoute").add("menuGetRoute", _menuGetRoute, { sequence: 1 });
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
                    _setCurrentMenu(menu, false);
                },
            });
            _updateURL(menu.id);
        },
        setCurrentMenu: (menu) => _setCurrentMenu(menu),
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
        router.addLockedKey("menu_id");
        const fetchLoadMenus = makeFetchLoadMenus();
        const menusData = await fetchLoadMenus();
        return makeMenus(env, menusData, fetchLoadMenus);
    },
};

registry.category("services").add("menu", menuService);
