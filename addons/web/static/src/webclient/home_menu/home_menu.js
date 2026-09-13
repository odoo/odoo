// @ts-check
/** @odoo-module native */

import {
    Component,
    onMounted,
    onWillRender,
    onWillUnmount,
    onWillUpdateProps,
    reactive,
    useRef,
    useState,
} from "@odoo/owl";
import { useSetupAction } from "@web/core/action_hook";
import { browser } from "@web/core/browser/browser";
import { hasTouch, isIosApp } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { _t } from "@web/core/translation";
import { useSortable } from "@web/core/utils/dnd";
import { useService } from "@web/core/utils/hooks";
import { parseHomeMenuConfig } from "@web/webclient/menus/menu_utils";

import { loadHomeMenuBadges, useHomeMenuBadgeUpdates } from "./badges.js";
import { ExpirationPanel } from "./expiration_panel.js";
import { gridRows } from "./grid_navigation.js";
import { HomeMenuGrid } from "./home_menu_grid.js";
import { useHomeMenuKeyboard } from "./home_menu_keyboard.js";
import { HomeMenuLayout, orderAfterDrag } from "./home_menu_layout.js";
import { useHomeMenuSearch } from "./home_menu_search.js";
import { SysAdminPanel } from "./sysadmin_panel.js";

/** @param {{ xmlid?: string, module?: string, models?: string[] }[]} apps */
function homeMenuAppsKey(apps) {
    return JSON.stringify(
        apps.map(({ xmlid, module, models }) => [xmlid, module, models]),
    );
}

const log = makeLogger("web.home_menu.grid");

const APPS_PER_ROW = 6;
const BADGE_DELAY = 200;
const DIRECT_JUMP_HOTKEYS = 9;

/** @typedef {import("@web/webclient/menus/menu_utils").AppEntry} HomeMenuApp */

const APPS_CONFIG_SHAPE = { order: Array, pinned: Array, hidden: Array };

const APP_PROP = {
    type: Object,
    shape: {
        actionID: Number,
        href: String,
        appID: Number,
        id: Number,
        label: String,
        parents: String,
        module: { type: String, optional: true },
        category: { type: String, optional: true },
        categorySequence: { type: Number, optional: true },
        models: { type: Array, element: String, optional: true },
        keywords: { type: Array, element: String, optional: true },
        searchTerms: { type: Array, element: String, optional: true },
        webIcon: {
            type: [
                Boolean,
                String,
                {
                    type: Object,
                    optional: 1,
                    shape: {
                        iconClass: String,
                        color: String,
                        backgroundColor: String,
                    },
                },
            ],
            optional: true,
        },
        webIconData: { type: String, optional: 1 },
        xmlid: { type: String, optional: true },
    },
};

/** @extends {Component<any, import("@web/env").OdooEnv>} */
export class HomeMenu extends Component {
    static template = "web.HomeMenu";
    static appTemplate = "web.HomeMenu.App";
    static components = { ExpirationPanel, SysAdminPanel };
    static props = {
        apps: { type: Array, element: APP_PROP },
        reorderApps: { type: Function },
        personal: { type: Boolean, optional: true },
        config: { type: Object, optional: true, shape: APPS_CONFIG_SHAPE },
        resetApps: { type: Function, optional: true },
        defaultConfig: { type: Object, optional: true, shape: APPS_CONFIG_SHAPE },
    };

    /**
     * @type {{
     *  isIosApp: boolean;
     *  editing: boolean;
     *  badges: Record<string, number>;
     *  layoutAnnouncement: string;
     * }}
     */
    state;
    /** @type {HomeMenuLayout} */
    layout;
    /** @type {boolean} */
    /** @type {ReturnType<typeof useHomeMenuSearch>} */
    search;

    /** @type {import("services").ServiceFactories["menu"]} */
    menus;
    /** @type {import("services").ServiceFactories["home_menu"]} */
    homeMenuService;
    /** @type {import("services").ServiceFactories["enterprise_subscription"]} */
    subscription;
    /** @type {import("@odoo/owl").Ref<HTMLElement>} */
    rootRef;
    setup() {
        useLifecycleLog(log);
        this.menus = useService("menu");
        this.homeMenuService = useService("home_menu");
        this.subscription = useService("enterprise_subscription");
        this.state = useState({
            isIosApp: isIosApp(),
            editing: false,
            badges: {},
            layoutAnnouncement: "",
        });
        this.search = useHomeMenuSearch({
            onQueryChanged: () => this.keyboard.clear(),
        });
        this._setupLayout();
        this.rootRef = useRef("root");

        this.grid = new HomeMenuGrid({
            apps: () => this.displayedApps,
            query: () => this.search.query,
            editing: () => this.state.editing,
            badges: () => this.state.badges,
            layout: this.layout,
            menus: this.menus,
        });
        onWillRender(() => this.grid.clear());

        this.keyboard = useHomeMenuKeyboard({
            rows: () => this.keyboardRows,
            activate: (index) => this._activate(index),
            fallback: () => this._openFirstMatch(),
            escape: () => this._onEscape(),
            isAvailable: (
                /** @type {EventTarget & Partial<Pick<Element, "closest">> | null} */ target,
            ) => !target?.closest?.(".o_app_edit_actions"),
            enterTarget: () => this.search.inputEl,
        });

        this._setupSorting();
        this._setupBadges();
        this._setupPropsSync();

        onMounted(() => {
            if (!hasTouch()) {
                this.search.focus();
            }
        });
    }

    _setupLayout() {
        this.layout = new HomeMenuLayout({
            config: useState(this.props.config ?? reactive(parseHomeMenuConfig(null))),
            defaultConfig: this.props.defaultConfig ?? parseHomeMenuConfig(null),
            orm: useService("orm"),
            personal: this.props.personal,
            onSaved: () => this.props.reorderApps(this.layout.config.order),
        });
        this.layout.state = useState(this.layout.state);
        useSetupAction({
            beforeLeave: () => this.layout.flushBeforeLeave(),
            beforeUnload: (/** @type {BeforeUnloadEvent} */ event) => {
                if (this.layout.unsaved) {
                    event.preventDefault();
                    event.returnValue = "";
                }
            },
        });
    }

    _setupSorting() {
        for (const [elements, onDrop] of /** @type {const} */ ([
            [".o_apps .o_draggable", this._sortAppDrop],
            [".o_pinned_apps .o_draggable", this._sortPinnedDrop],
        ])) {
            useSortable({
                enable: () => this._enableAppsSorting(),
                ref: this.rootRef,
                elements,
                ignore: ".o_app_edit_actions",
                cursor: "move",
                onWillStartDrag: (params) => this._sortStart(params),
                onDrop: (params) => onDrop.call(this, params),
            });
        }
    }

    _setupBadges() {
        this.badgeRequest = 0;
        useHomeMenuBadgeUpdates(this.env, () => this._loadBadges());
        onMounted(() => {
            this.badgeTimer = browser.setTimeout(() => this._loadBadges(), BADGE_DELAY);
        });
        onWillUnmount(() => {
            browser.clearTimeout(this.badgeTimer);
            this.badgeRequest++;
        });
    }

    _setupPropsSync() {
        this.appsKey = homeMenuAppsKey(this.props.apps);
        onWillUpdateProps((nextProps) => {
            const appsKey = homeMenuAppsKey(nextProps.apps);
            const appsChanged = appsKey !== this.appsKey;
            const configChanged =
                Boolean(nextProps.config) && nextProps.config !== this.props.config;
            if (appsChanged) {
                this.appsKey = appsKey;
                this._loadBadges(nextProps.apps);
            }
            if (configChanged) {
                this.layout.setConfig(reactive(nextProps.config, () => this.render()));
            }
            if (nextProps.defaultConfig) {
                this.layout.defaultConfig = nextProps.defaultConfig;
            }
            if (appsChanged || configChanged) {
                this.keyboard.clear();
            }
        });
    }

    /** @returns {HomeMenuApp[]} */
    get displayedApps() {
        return this.props.apps;
    }

    /** @returns {boolean} */
    get canEditLayout() {
        return true;
    }

    /** @returns {boolean} */
    get hasCustomLayout() {
        return this.layout.isCustomised;
    }

    /** @returns {boolean} */
    get canSetCompanyDefault() {
        return this.layout.canSetCompanyDefault;
    }

    /** @param {HomeMenuApp} app */
    badgeFor(app) {
        return this.grid.badgeOf(app);
    }

    /** @param {HomeMenuApp} app */
    pinTitle(app) {
        return this.layout.isPinned(app) ? _t("Unpin") : _t("Pin");
    }

    /** @param {HomeMenuApp} app */
    hideTitle(app) {
        return this.layout.isHidden(app) ? _t("Show") : _t("Hide");
    }

    /** @returns {number} */
    get directJumpHotkeys() {
        return DIRECT_JUMP_HOTKEYS;
    }

    /** @param {HomeMenuApp} menu */
    _openMenu(menu) {
        return this.menus.selectMenu(menu);
    }

    /** @param {HomeMenuApp[]} [apps] */
    async _loadBadges(apps) {
        const request = ++this.badgeRequest;
        const badges = await loadHomeMenuBadges(
            /** @type {import("@web/env").OdooEnv} */ (
                /** @type {unknown} */ (this.env)
            ),
            apps ?? this.displayedApps,
            { refresh: true },
        );
        if (request === this.badgeRequest) {
            this.state.badges = badges;
        }
    }

    /** @param {HomeMenuApp} app */
    _togglePinned(app) {
        return this.layout.togglePinned(app);
    }

    /** @param {HomeMenuApp} app */
    _toggleHidden(app) {
        return this.layout.toggleHidden(app);
    }

    _resetLayout() {
        const { order, saved } = this.layout.reset();
        this.props.resetApps?.(order);
        return saved;
    }

    async _setCompanyDefault() {
        await this.layout.setCompanyDefault();
        this.render();
    }

    _toggleEditing() {
        this.state.editing = !this.state.editing;
        this.keyboard.clear();
    }

    _onEscape() {
        if (this.search.query) {
            this.search.clear();
        } else if (this.state.editing) {
            this._toggleEditing();
        } else {
            this.homeMenuService.toggle(false);
        }
    }

    /** @param {number} index */
    keyboardItem(index) {
        const apps = this.grid.visibleApps;
        return index < apps.length
            ? apps[index]
            : this.grid.menuMatches[index - apps.length];
    }

    /** @param {number} index */
    _activate(index) {
        const item = this.keyboardItem(index);
        if (!item) {
            return;
        }
        return index < this.grid.visibleApps.length
            ? this._openMenu(/** @type {HomeMenuApp} */ (item))
            : this.menus.selectMenu(item);
    }

    _openFirstMatch() {
        if (!this.search.query) {
            return;
        }
        const [app] = this.grid.unpinnedApps;
        if (app) {
            return this._openMenu(app);
        }
        const [menu] = this.grid.menuMatches;
        if (menu) {
            return this.menus.selectMenu(menu);
        }
    }

    /** @param {import("@web/webclient/menus/menu_utils").MenuEntry} menu */
    _onMenuResultClick(menu) {
        return this.menus.selectMenu(menu);
    }

    /** @returns {number[][]} */
    get keyboardRows() {
        return gridRows(
            this.grid.keyboardRows,
            this.appsPerRow,
            this.grid.menuMatches.length,
        );
    }

    get appsPerRow() {
        const row = this.rootRef.el?.querySelector(".o_apps.row, .o_pinned_apps .row");
        const tile = row?.firstElementChild;
        if (row && tile && tile.getBoundingClientRect().width) {
            return Math.max(
                1,
                Math.round(
                    row.getBoundingClientRect().width /
                        tile.getBoundingClientRect().width,
                ),
            );
        }
        return this.env.isSmall ? (this.state.isIosApp ? 1 : 4) : APPS_PER_ROW;
    }

    /** @param {HomeMenuApp} app */
    appOrder(app) {
        return this.layout.isPinned(app)
            ? this.layout.config.pinned
            : this.displayedApps
                  .filter((item) => !this.layout.isPinned(item))
                  .flatMap((item) => (item.xmlid ? [item.xmlid] : []));
    }

    /**
     * @param {HomeMenuApp} app
     * @param {number} delta
     */
    canMoveApp(app, delta) {
        const bounds = this.grid.moveBounds.get(app.xmlid ?? "");
        return Boolean(
            bounds && bounds.index + delta >= 0 && bounds.index + delta < bounds.length,
        );
    }

    /**
     * @param {HomeMenuApp} app
     * @param {number} delta
     */
    moveApp(app, delta) {
        this.grid.clear();
        if (!this.canMoveApp(app, delta)) {
            return;
        }
        const order = [...this.appOrder(app)];
        const from = order.indexOf(app.xmlid ?? "");
        [order[from], order[from + delta]] = [order[from + delta], order[from]];
        this.keyboard.clear();
        this.state.layoutAnnouncement = _t("%(app)s moved to position %(position)s", {
            app: app.label,
            position: from + delta + 1,
        });
        if (this.layout.isPinned(app)) {
            return this.layout.setPinnedOrder(order);
        }
        this.props.reorderApps(order);
        return this.layout.setOrder(order);
    }

    showAllMenuResults() {
        this.search.openPalette();
    }

    _enableAppsSorting() {
        return this.state.editing;
    }

    /** @param {import("@web/core/utils/dnd/sortable").DropParams} params */
    _sortAppDrop({ element, previous }) {
        const movedId = /** @type {HTMLElement} */ (element.querySelector(".o_app"))
            .dataset.menuXmlid;
        if (movedId === undefined) {
            return;
        }
        const order = orderAfterDrag(
            this.displayedApps.flatMap((app) =>
                app.xmlid === undefined ? [] : [app.xmlid],
            ),
            movedId,
            /** @type {HTMLElement} */ (previous?.querySelector(".o_app"))?.dataset
                .menuXmlid,
        );
        if (!order) {
            return;
        }
        this.props.reorderApps(order);
        return this.layout.setOrder(order);
    }

    /** @param {import("@web/core/utils/dnd/sortable").DropParams} params */
    _sortPinnedDrop({ element, previous }) {
        const moved = /** @type {HTMLElement | null} */ (
            element.querySelector(".o_app")
        )?.dataset.menuXmlid;
        const after = /** @type {HTMLElement | undefined} */ (
            previous?.querySelector(".o_app")
        )?.dataset.menuXmlid;
        const order = moved && orderAfterDrag(this.layout.config.pinned, moved, after);
        if (order) {
            return this.layout.setPinnedOrder(order);
        }
    }

    /** @param {import("@web/core/utils/dnd/sortable").SortableHandlerParams} params */
    _sortStart({ element, addClass }) {
        addClass(
            /** @type {HTMLElement} */ (element.querySelector(".o_app")),
            "o_dragged_app",
        );
    }

    /** @param {HomeMenuApp} app */
    _onAppClick(app) {
        this._openMenu(app);
    }

    /** @param {number} index */
    _onItemFocus(index) {
        this.keyboard.focus(index);
    }
}
