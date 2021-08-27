/** @odoo-module **/

import { browser } from "../core/browser/browser";
import { registry } from "../core/registry";
import { session } from "@web/session";

const loadMenusUrl = `/web/webclient/load_menus`;

/**
 * Traverses the given menu tree, executes the given callback for each node with
 * the node itself and the list of its ancestors as arguments.
 *
 * @param {Object} tree tree of menus as exported by the menus service
 * @param {Function} cb
 * @param {[Object]} [parents] the ancestors of the tree root, if any
 */
function traverseMenuTree(tree, cb, parents = []) {
    cb(tree, parents);
    tree.childrenTree.forEach((c) => traverseMenuTree(c, cb, parents.concat([tree])));
}

/**
 * Computes the "apps" and "menuItems" from a given menu tree.
 *
 * @param {Object} menuTree tree of menus as exported by the menus service
 * @returns {Object} with keys "apps" and "menuItems" (HomeMenu props)
 */
export function computeAppsAndMenuItems(menuTree) {
    const apps = [];
    const menuItems = [];
    traverseMenuTree(menuTree, (menuItem, parents) => {
        if (!menuItem.id || !menuItem.actionID) {
            return;
        }
        const isApp = menuItem.id === menuItem.appID;
        const item = {
            parents: parents
                .slice(1)
                .map((p) => p.name)
                .join(" / "),
            label: menuItem.name,
            id: menuItem.id,
            xmlid: menuItem.xmlid,
            actionID: menuItem.actionID,
            appID: menuItem.appID,
        };
        if (isApp) {
            if (menuItem.webIconData) {
                item.webIconData = menuItem.webIconData;
            } else {
                const [iconClass, color, backgroundColor] = (menuItem.webIcon || "").split(",");
                if (backgroundColor !== undefined) {
                    // Could split in three parts?
                    item.webIcon = { iconClass, color, backgroundColor };
                } else {
                    item.webIconData = "/web_enterprise/static/img/default_icon_app.png";
                }
            }
        } else {
            item.menuID = parents[1].id;
        }
        if (isApp) {
            apps.push(item);
        } else {
            menuItems.push(item);
        }
    });
    return { apps, menuItems };
}

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
    return {
        getAll() {
            return Object.values(menusData);
        },
        getApps() {
            return this.getMenu("root").children.map((mid) => this.getMenu(mid));
        },
        getMenu(menuID) {
            return menusData[menuID];
        },
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
            await env.services.action.doAction(menu.actionID, { clearBreadcrumbs: true });
            this.setCurrentMenu(menu);
        },
        setCurrentMenu(menu) {
            menu = typeof menu === "number" ? this.getMenu(menu) : menu;
            if (menu && menu.appID !== currentAppId) {
                currentAppId = menu.appID;
                env.bus.trigger("MENUS:APP-CHANGED");
                // FIXME: lock API: maybe do something like
                // pushState({menu_id: ...}, { lock: true}); ?
                env.services.router.pushState({ menu_id: menu.id }, { lock: true });
            }
        },
        async reload() {
            if (fetchLoadMenus) {
                menusData = await fetchLoadMenus(true);
                env.bus.trigger("MENUS:APP-CHANGED");
            }
        },
    };
}

export const menuService = {
    dependencies: ["action", "router"],
    async start(env) {
        const fetchLoadMenus = makeFetchLoadMenus();
        const menusData = await fetchLoadMenus();
        return makeMenus(env, menusData, fetchLoadMenus);
    },
};

registry.category("services").add("menu", menuService);
