import { computed, signal, t, usePlugin } from "@odoo/owl";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { IndexedDB } from "@web/core/utils/indexed_db";
import { session } from "@web/session";
import { user } from "@web/core/user";

function evaluateInvisible(menus) {
    Object.values(menus).forEach((menu) => {
        menu.invisible = evaluateBooleanExpr(menu.webInvisible, user.evalContext);
        delete menu.webInvisible;
    });
    return menus;
}

export const menuService = {
    dependencies: ["action"],
    async start(env, { action }) {
        /**
         * @param {boolean} [reload=false]
         */
        async function fetchMenus(reload) {
            if (!reload && odoo.loadMenusPromise) {
                return odoo.loadMenusPromise;
            }
            const res = await fetch(loadMenusUrl, { cache: "no-store" });
            if (!res.ok) {
                throw new Error("Error while fetching menus");
            }
            return res.json();
        }

        /**
         * @param {string | number} menuId
         */
        function getMenu(menuId) {
            return menusData()[menuId];
        }

        /**
         * @param {string | number | Record<string, any>} menu
         */
        function setCurrentMenu(menu) {
            menu = typeof menu === "number" ? getMenu(menu) : menu;
            if (menu && menu.appID !== currentAppId()) {
                currentAppId.set(menu.appID ?? null);
                sessionStorage.setItem("menu_id", menu.appID);
                env.bus.trigger("MENUS:APP-CHANGED");
            }
        }

        const currentAppId = signal(null, {
            type: t.or([t.string(), t.number(), t.literal(null)]),
        });
        const menusData = signal(null, { type: t.record(t.string()) });

        const menuDB = new IndexedDB("webclient_menu", session.registry_hash);
        const table = "menu";
        const debugMode = usePlugin(DebugModePlugin);
        const key = JSON.stringify({ debug: debugMode.isActive() });
        const loadMenusUrl = `/web/webclient/load_menus`;

        const storedMenus = await menuDB.read(table, key);
        if (storedMenus) {
            fetchMenus().then((res) => {
                if (res) {
                    const fetchedMenus = JSON.stringify(res);
                    if (fetchedMenus !== storedMenus) {
                        menuDB.write(table, key, fetchedMenus);
                        menusData.set(evaluateInvisible(res));
                        env.bus.trigger("MENUS:APP-CHANGED");
                    }
                }
            });
            menusData.set(evaluateInvisible(JSON.parse(storedMenus)));
        } else {
            const fetchedMenus = await fetchMenus();
            if (fetchedMenus) {
                menuDB.write(table, key, JSON.stringify(fetchedMenus));
            }
            menusData.set(evaluateInvisible(fetchedMenus));
        }

        return {
            getAll: computed(() => Object.values(menusData())),
            getApps: computed(() =>
                getMenu("root")
                    .children.filter((mID) => !getMenu(mID).invisible)
                    .map(getMenu)
            ),
            getCurrentApp: computed(() => currentAppId() && getMenu(currentAppId())),
            getMenu,
            getMenuAsTree(menuID) {
                const menu = getMenu(menuID);
                if (!menu.childrenTree) {
                    menu.childrenTree = menu.children
                        .filter((mID) => !getMenu(mID).invisible)
                        .map((mid) => this.getMenuAsTree(mid));
                }
                return menu;
            },
            async reload() {
                menusData.set(evaluateInvisible(await fetchMenus(true)));
                env.bus.trigger("MENUS:APP-CHANGED");
            },
            async selectMenu(menu) {
                menu = typeof menu === "number" ? getMenu(menu) : menu;
                if (!menu.actionID) {
                    return;
                }
                await action.doAction(menu.actionID, {
                    clearBreadcrumbs: true,
                    onActionReady: () => {
                        setCurrentMenu(menu);
                    },
                });
            },
            setCurrentMenu,
        };
    },
};

registry.category("services").add("menu", menuService);
