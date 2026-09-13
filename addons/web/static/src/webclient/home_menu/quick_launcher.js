// @ts-check
/** @odoo-module native */

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { AppEvent } from "@web/core/events";
import { useBus, useService } from "@web/core/utils/hooks";
import { menuUsage } from "@web/webclient/menus/menu_usage";

import { appBadge, loadHomeMenuBadges, useHomeMenuBadgeUpdates } from "./badges.js";
import { pinnedApps, shownApps, useHomeMenuLayoutSync } from "./home_menu_layout.js";
import { computeHomeMenuLayout } from "./home_menu_service.js";

const TILES = 12;

/** @extends {Component<any, import("@web/env").OdooEnv>} */
export class QuickLauncher extends Component {
    static template = "web.QuickLauncher";
    static props = {
        close: Function,
        showAllApps: { type: Boolean, optional: true },
    };
    static defaultProps = { showAllApps: true };

    /** @type {import("services").ServiceFactories["menu"]} */
    menus;
    /** @type {import("services").ServiceFactories["home_menu"]} */
    homeMenu;
    /** @type {import("services").ServiceFactories["command"]} */
    command;
    /** @type {{ badges: Record<string, number> }} */
    state;
    /** @type {import("./home_menu.js").HomeMenuApp[]} */
    apps;

    badgeRequest = 0;
    composing = false;
    /** @type {import("./home_menu.js").HomeMenuApp[]} */
    catalog = [];

    setup() {
        this.menus = useService("menu");
        this.homeMenu = useService("home_menu");
        this.command = useService("command");
        this.state = useState({ badges: {} });
        const refresh = () => {
            this._loadCatalog();
            this.loadBadges();
            this.render();
        };
        this._loadCatalog();
        useHomeMenuLayoutSync(refresh);
        useBus(this.env.bus, AppEvent.MENUS_APP_CHANGED, refresh);
        useHomeMenuBadgeUpdates(this.env, () => this.loadBadges());
        onWillUnmount(() => {
            this.badgeRequest++;
        });
        onMounted(() => this.loadBadges());
    }

    _loadCatalog() {
        const { apps, config } = computeHomeMenuLayout(this.menus);
        this.catalog = apps;
        this.apps = this._pickApps(apps, config);
    }

    async loadBadges() {
        const request = ++this.badgeRequest;
        const badges = await loadHomeMenuBadges(this.env, this.catalog);
        if (request === this.badgeRequest) {
            this.state.badges = badges;
        }
    }

    /**
     * @param {import("./home_menu.js").HomeMenuApp[]} apps
     * @param {import("@web/webclient/menus/menu_utils").HomeMenuConfig} config
     */
    _pickApps(apps, config) {
        const shown = shownApps(config, apps);
        const ordered = [
            ...pinnedApps(config, shown),
            ...menuUsage.rank(shown),
            ...shown,
        ];
        return [...new Set(ordered)].slice(0, TILES);
    }

    /** @param {import("./home_menu.js").HomeMenuApp} app */
    badgeFor(app) {
        return appBadge(this.state.badges, app);
    }

    /** @param {import("./home_menu.js").HomeMenuApp} app */
    onAppClick(app) {
        const opened = this.menus.selectMenu(app);
        this.props.close();
        return opened;
    }

    onAllAppsClick() {
        const opened = this.homeMenu.toggle(true);
        this.props.close();
        return opened;
    }

    onCompositionStart() {
        this.composing = true;
    }

    /** @param {CompositionEvent} ev */
    onCompositionEnd(ev) {
        this.composing = false;
        this.onSearchInput(/** @type {InputEvent} */ (/** @type {unknown} */ (ev)));
    }

    /** @param {InputEvent} ev */
    onSearchInput(ev) {
        if (this.composing || ev.isComposing) {
            return;
        }
        const typed = /** @type {HTMLInputElement} */ (ev.target).value.trim();
        if (!typed) {
            return;
        }
        this.props.close();
        this.command.openMainPalette(/** @type {any} */ ({ searchValue: `/${typed}` }));
    }
}
