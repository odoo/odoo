// @ts-check
/** @odoo-module native */

import {
    Component,
    markRaw,
    onMounted,
    onWillDestroy,
    onWillUnmount,
    reactive,
    xml,
} from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { AppEvent } from "@web/core/events";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { Mutex } from "@web/core/utils/concurrency";
import { useBus, useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import {
    ControllerNotFoundError,
    standardActionServiceProps,
} from "@web/webclient/actions";
import {
    flattenMenuTree,
    parseHomeMenuConfig,
    readHomeMenuConfig,
    reorderApps,
} from "@web/webclient/menus/menu_utils";

import { HomeMenu } from "./home_menu.js";
import { useHomeMenuLayoutSync } from "./home_menu_layout.js";

export class HomeMenuState {
    hasHomeMenu = false;
    hasBackgroundAction = false;
    /** @type {HomeMenuAction | null} */
    currentAction = null;

    /** @param {import("@web/env").OdooEnv} env */
    constructor(env) {
        this.action = markRaw(env.services.action);
        this.mutex = markRaw(new Mutex());
        this.bus = markRaw(env.bus);
        this.onToggle = () => {
            document.body.classList.toggle("o_home_menu_background", this.hasHomeMenu);
        };
        this.bus.addEventListener(AppEvent.HOME_MENU_TOGGLED, this.onToggle);
    }

    destroy() {
        this.bus.removeEventListener(AppEvent.HOME_MENU_TOGGLED, this.onToggle);
        this.currentAction = null;
    }

    /** @param {boolean} [show] */
    async toggle(show) {
        const { action } = this;
        const epoch = action.navigation.epoch;
        return this.mutex.exec(async () => {
            show = show === undefined ? !this.hasHomeMenu : Boolean(show);
            if (show === this.hasHomeMenu) {
                return;
            }
            if (show) {
                if (action.navigation.epoch === epoch) {
                    await action.doAction("menu");
                }
                return;
            }
            try {
                await action.restore();
            } catch (err) {
                if (!(err instanceof ControllerNotFoundError)) {
                    throw err;
                }
            }
        });
    }
}

/**
 * @param {import("services").ServiceFactories["menu"]} menus
 * @returns {{
 *  apps: import("./home_menu.js").HomeMenuApp[],
 *  config: import("@web/webclient/menus/menu_utils").HomeMenuConfig,
 *  defaultConfig: import("@web/webclient/menus/menu_utils").HomeMenuConfig,
 *  defaultOrder: string[],
 *  personal: boolean,
 * }}
 */
export function computeHomeMenuLayout(menus) {
    const defaultConfig = parseHomeMenuConfig(session.homemenu_default_config);
    const own = readHomeMenuConfig(user.settings?.homemenu_config);
    const config = own ?? parseHomeMenuConfig(defaultConfig);
    const apps = [...flattenMenuTree(menus.getMenuAsTree("root")).apps];
    const defaultOrder = apps.flatMap((app) =>
        app.xmlid === undefined ? [] : [app.xmlid],
    );
    if (config.order.length) {
        reorderApps(apps, config.order);
    }
    return { apps, config, defaultConfig, defaultOrder, personal: own !== null };
}

/**
 * @param {import("services").ServiceFactories["menu"]} menus
 * @returns {import("./home_menu.js").HomeMenu["props"]}
 */
export function computeHomeMenuProps(menus) {
    const layout = computeHomeMenuLayout(menus);
    const { defaultConfig, defaultOrder } = layout;
    const apps = reactive(layout.apps);
    const config = reactive(layout.config);
    return {
        apps,
        config,
        defaultConfig,
        personal: layout.personal,
        reorderApps: (/** @type {string[]} */ order) => reorderApps(apps, order),
        resetApps: (/** @type {string[]} */ order) => {
            reorderApps(apps, defaultOrder);
            if (order?.length) {
                reorderApps(apps, order);
            }
        },
    };
}

const log = makeLogger("web.home_menu");

export class HomeMenuAction extends Component {
    static components = { HomeMenu };
    static target = "current";
    static props = { ...standardActionServiceProps };
    static template = xml`<HomeMenu t-props="homeMenuProps"/>`;
    static displayName = _t("Home");

    /** @type {import("services").ServiceFactories["menu"]} */
    menus;
    /** @type {import("services").ServiceFactories["home_menu"]} */
    homeMenu;

    setup() {
        this.menus = useService("menu");
        this.homeMenu = useService("home_menu");
        this.homeMenuProps = computeHomeMenuProps(this.menus);
        this.homeMenu.currentAction = markRaw(this);
        this.homeMenu.hasHomeMenu = true;
        this.homeMenu.hasBackgroundAction = this.env.config.breadcrumbs.length > 0;
        log.lifecycle("setup", () => ({ crumbs: this.env.config.breadcrumbs.length }));
        onMounted(() => {
            log.lifecycle("mounted", () => ({
                isCurrent: this.homeMenu.currentAction === this,
            }));
            this.env.bus.trigger(AppEvent.HOME_MENU_TOGGLED);
        });
        onWillUnmount(() => {
            log.lifecycle("willUnmount", () => ({
                isCurrent: this.homeMenu.currentAction === this,
            }));
            this._release();
            this.env.bus.trigger(AppEvent.HOME_MENU_TOGGLED);
        });
        onWillDestroy(() => {
            log.lifecycle("willDestroy", () => ({
                isCurrent: this.homeMenu.currentAction === this,
            }));
            this._release();
        });
        const refresh = () => {
            this.homeMenuProps = computeHomeMenuProps(this.menus);
            this.render();
        };
        useBus(this.env.bus, AppEvent.MENUS_APP_CHANGED, refresh);
        useHomeMenuLayoutSync(refresh);
    }
    _release() {
        if (this.homeMenu.currentAction !== this) {
            return;
        }
        log.logic("release");
        this.homeMenu.currentAction = null;
        this.homeMenu.hasHomeMenu = false;
        this.homeMenu.hasBackgroundAction = false;
    }
}

export const homeMenuService = {
    dependencies: ["action"],
    /** @param {import("@web/env").OdooEnv} env */
    start(env) {
        const state = reactive(new HomeMenuState(env));
        return state;
    },
};

registry.category("actions").add("menu", HomeMenuAction);
registry.category("services").add("home_menu", homeMenuService);
