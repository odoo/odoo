import {
    asyncComputed,
    computed,
    onWillStart,
    Plugin,
    signal,
    t,
    useEffect,
    usePlugin,
} from "@odoo/owl";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import { GlobalBusPlugin } from "@web/core/global_bus_plugin";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { IndexedDB } from "@web/core/utils/indexed_db";
import { session } from "@web/session";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

const MENU_TABLE = "menu";
const LOAD_MENUS_URL = `/web/webclient/load_menus`;

export class MenuPlugin extends Plugin {
    /** @private */
    action = usePlugin(ActionPlugin);
    /** @private */
    bus = usePlugin(GlobalBusPlugin).bus;
    /** @private */
    debugMode = usePlugin(DebugModePlugin);
    /** @private */
    menuDB = new IndexedDB("webclient_menu", session.registry_hash);
    /** @private */
    currentAppId = signal(null, {
        type: t.or([t.string(), t.number(), t.literal(null)]),
    });

    /** @private */
    forceReload = false;

    getAll = computed(() => Object.values(this.menusData()));
    getApps = computed(() => this.getMenu("root").children.map((id) => this.getMenu(id)));
    getCurrentApp = computed(() => this.currentAppId() && this.getMenu(this.currentAppId()));

    /** @private */
    key = computed(() => JSON.stringify({ debug: this.debugMode.isActive() }));
    /** @private */
    storedMenus = asyncComputed(async () => await this.menuDB.read(MENU_TABLE, this.key()), {
        initial: null,
    });
    /** @private */
    fetchedMenus = asyncComputed(
        async ({ abortSignal }) => {
            const forceReload = this.forceReload;
            this.forceReload = false;
            return await this.fetchMenus(forceReload, abortSignal);
        },
        { initial: null }
    );
    /** @private */
    menusData = computed(() => this.fetchedMenus() || JSON.parse(this.storedMenus() || "{}"));

    setup() {
        onWillStart(async () => {
            await this.storedMenus.currentPromise();
            if (!this.storedMenus()) {
                await this.fetchedMenus.currentPromise();
            }
        });
        useEffect(() => {
            const error = this.fetchedMenus.error();
            if (error) {
                Promise.reject(error);
            }
        });
        useEffect(() => {
            const storedMenus = this.storedMenus();
            const fetchedMenus = this.fetchedMenus();

            if (fetchedMenus) {
                const stringifiedFetchedMenus = JSON.stringify(fetchedMenus);
                if (stringifiedFetchedMenus !== storedMenus) {
                    this.menuDB.write(MENU_TABLE, this.key(), stringifiedFetchedMenus);
                    this.bus.trigger("MENUS:APP-CHANGED");
                }
            }
        });
    }

    /**
     * @private
     * @param {boolean} [reload=false]
     * @param {AbortSignal} abortSignal
     */
    async fetchMenus(reload, abortSignal) {
        if (!reload && odoo.loadMenusPromise) {
            return odoo.loadMenusPromise;
        }
        const res = await fetch(LOAD_MENUS_URL, { cache: "no-store", signal: abortSignal });
        if (!res.ok) {
            throw new Error("Error while fetching menus");
        }
        return res.json();
    }

    /**
     * @param {string | number} menuId
     */
    getMenu(menuId) {
        return this.menusData()[menuId];
    }

    getMenuAsTree(menuID) {
        const menu = this.getMenu(menuID);
        if (!menu.childrenTree) {
            menu.childrenTree = menu.children.map((mid) => this.getMenuAsTree(mid));
        }
        return menu;
    }

    async reload() {
        this.forceReload = true;
        await this.fetchedMenus.refresh();
        await this.fetchedMenus.currentPromise();
    }

    async selectMenu(menu) {
        menu = typeof menu === "number" ? this.getMenu(menu) : menu;
        if (!menu.actionID) {
            return;
        }
        await this.action.doAction(menu.actionID, {
            clearBreadcrumbs: true,
            onActionReady: () => {
                this.setCurrentMenu(menu);
            },
        });
    }

    /**
     * @param {string | number | Record<string, any>} menu
     */
    setCurrentMenu(menu) {
        menu = typeof menu === "number" ? this.getMenu(menu) : menu;
        if (menu && menu.appID !== this.currentAppId()) {
            this.currentAppId.set(menu.appID ?? null);
            sessionStorage.setItem("menu_id", menu.appID);
            this.bus.trigger("MENUS:APP-CHANGED");
        }
    }
}

services.add(MenuPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the menu service are removed
 * -----------------------------------------------------------------------------
 */
export const menuService = {
    dependencies: ["action"],
    start() {
        return usePlugin(MenuPlugin);
    },
};

registry.category("services").add("menu", menuService);
