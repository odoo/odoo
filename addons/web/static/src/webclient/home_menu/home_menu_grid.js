// @ts-check
/** @odoo-module native */

import { makeLogger } from "@web/core/debug/debug_logger";
import { _t } from "@web/core/translation";
import { fuzzyLookup } from "@web/core/utils/search";
import { menuUsage } from "@web/webclient/menus/menu_usage";
import {
    appSearchKey,
    flattenMenuTree,
    menuSearchKey,
} from "@web/webclient/menus/menu_utils";

import { appBadge } from "./badges.js";
import { pinnedApps, shownApps } from "./home_menu_layout.js";

/** @typedef {import("@web/webclient/menus/menu_utils").AppEntry} HomeMenuApp */

const APPS_PER_ROW = 6;
const SECTIONED_FROM = APPS_PER_ROW * 2;
const RECENT_APPS = 6;
const ATTENTION_APPS = 6;
const MENU_MATCHES = 8;

const EMPTY_MENU_TREE = { childrenTree: [] };

const log = makeLogger("web.home_menu.grid");

export class HomeMenuGrid {
    /**
     * @param {{
     *  apps: () => HomeMenuApp[],
     *  query: () => string,
     *  editing: () => boolean,
     *  badges: () => Record<string, number>,
     *  layout: import("./home_menu_layout.js").HomeMenuLayout,
     *  menus: import("services").ServiceFactories["menu"],
     * }} params
     */
    constructor({ apps, query, editing, badges, layout, menus }) {
        this.apps = apps;
        this.query = query;
        this.editing = editing;
        this.badges = badges;
        this.layout = layout;
        this.menus = menus;
        /** @type {Map<string, any>} */
        this.derived = new Map();
    }

    clear() {
        this.derived.clear();
    }

    /**
     * @template T
     * @param {string} key
     * @param {() => T} compute
     * @returns {T}
     */
    _memo(key, compute) {
        if (!this.derived.has(key)) {
            const end = log.perf(key);
            const value = compute.call(this);
            end({ size: Array.isArray(value) ? value.length : undefined });
            this.derived.set(key, value);
        }
        return this.derived.get(key);
    }

    /** @returns {Map<string, { index: number, length: number }>} */
    get moveBounds() {
        return this._memo("moveBounds", () => {
            const pinned = this.layout.config.pinned;
            const pinnedIds = new Set(pinned);
            const unpinned = this.apps().flatMap(({ xmlid }) =>
                xmlid && !pinnedIds.has(xmlid) ? [xmlid] : [],
            );
            const bounds = new Map();
            for (const order of [pinned, unpinned]) {
                order.forEach((id, index) =>
                    bounds.set(id, { index, length: order.length }),
                );
            }
            return bounds;
        });
    }

    /** @param {HomeMenuApp} app */
    badgeOf(app) {
        return appBadge(this.badges(), app);
    }

    get keyboardRows() {
        return this._memo("keyboardRows", () => [
            this.pinnedApps.length,
            ...this.appSections.map((section) => section.apps.length),
        ]);
    }

    /** @returns {ReturnType<HomeMenuGrid["_visibleApps"]>} */
    get visibleApps() {
        return this._memo("visibleApps", this._visibleApps);
    }

    /** @returns {ReturnType<HomeMenuGrid["_appSections"]>} */
    get appSections() {
        return this._memo("appSections", this._appSections);
    }

    /** @returns {ReturnType<HomeMenuGrid["_shownApps"]>} */
    get shownApps() {
        return this._memo("shownApps", this._shownApps);
    }

    /** @returns {ReturnType<HomeMenuGrid["_pinnedApps"]>} */
    get pinnedApps() {
        return this._memo("pinnedApps", this._pinnedApps);
    }

    /** @returns {ReturnType<HomeMenuGrid["_unpinnedApps"]>} */
    get unpinnedApps() {
        return this._memo("unpinnedApps", this._unpinnedApps);
    }

    /** @returns {ReturnType<HomeMenuGrid["_recentApps"]>} */
    get recentApps() {
        return this._memo("recentApps", this._recentApps);
    }

    /** @returns {ReturnType<HomeMenuGrid["_attentionApps"]>} */
    get attentionApps() {
        return this._memo("attentionApps", this._attentionApps);
    }

    /** @returns {ReturnType<HomeMenuGrid["_menuMatches"]>} */
    get menuMatches() {
        return this._memo("menuMatches", this._menuMatches);
    }

    /** @returns {ReturnType<HomeMenuGrid["_searchSummary"]>} */
    get searchSummary() {
        return this._memo("searchSummary", this._searchSummary);
    }

    /** @returns {HomeMenuApp[]} */
    _visibleApps() {
        return [
            ...this.pinnedApps,
            ...this.appSections.flatMap((section) => section.apps),
        ];
    }

    /** @returns {{ category: string, apps: HomeMenuApp[], offset: number }[]} */
    _appSections() {
        const apps = this.unpinnedApps;
        const flat = [{ category: "", apps, offset: this.pinnedApps.length }];
        if (this.query() || this.editing() || apps.length <= SECTIONED_FROM) {
            return flat;
        }
        /** @type {Map<string, { apps: HomeMenuApp[], sequence: number }>} */
        const byCategory = new Map();
        for (const app of apps) {
            const category = app.category || _t("Other");
            const section = byCategory.get(category);
            if (section) {
                section.apps.push(app);
            } else {
                // An app whose module names no category heads no group of its
                // own, so "Other" collects them and sorts after every real
                // heading rather than at ir.module.category's implicit 0.
                const sequence = app.category ? app.categorySequence || 0 : Infinity;
                byCategory.set(category, { apps: [app], sequence });
            }
        }
        if (byCategory.size < 2) {
            return flat;
        }
        const ordered = [...byCategory].sort(
            ([leftName, left], [rightName, right]) =>
                left.sequence - right.sequence || leftName.localeCompare(rightName),
        );
        let offset = this.pinnedApps.length;
        return ordered.map(([category, { apps: sectionApps }]) => {
            const section = { category, apps: sectionApps, offset };
            offset += sectionApps.length;
            return section;
        });
    }

    /** @returns {HomeMenuApp[]} */
    _shownApps() {
        return this.editing()
            ? this.apps()
            : shownApps(this.layout.config, this.apps());
    }

    /** @returns {HomeMenuApp[]} */
    _pinnedApps() {
        return this.query() ? [] : pinnedApps(this.layout.config, this.shownApps);
    }

    /** @returns {HomeMenuApp[]} */
    _unpinnedApps() {
        if (this.query()) {
            return fuzzyLookup(this.query(), this.apps(), appSearchKey, {
                preNormalized: true,
            });
        }
        return this.shownApps.filter((app) => !this.layout.isPinned(app));
    }

    /** @returns {HomeMenuApp[]} */
    _recentApps() {
        return this.query() ? [] : menuUsage.rank(this.visibleApps, RECENT_APPS);
    }

    /** @returns {HomeMenuApp[]} */
    _attentionApps() {
        if (this.query() || this.editing()) {
            return [];
        }
        return this.visibleApps
            .filter((app) => this.badgeOf(app).count > 0)
            .sort((a, b) => this.badgeOf(b).count - this.badgeOf(a).count)
            .slice(0, ATTENTION_APPS);
    }

    /** @returns {import("@web/webclient/menus/menu_utils").MenuEntry[]} */
    _menuMatches() {
        if (!this.query()) {
            return [];
        }
        const { menuItems } = flattenMenuTree(
            this.menus.getMenuAsTree?.("root") ?? EMPTY_MENU_TREE,
        );
        return fuzzyLookup(this.query(), menuItems, menuSearchKey, {
            preNormalized: true,
        }).slice(0, MENU_MATCHES);
    }

    /** @returns {string} */
    _searchSummary() {
        if (!this.query()) {
            return "";
        }
        const appCount = this.unpinnedApps.length;
        const menuCount = this.menuMatches.length;
        if (!appCount && !menuCount) {
            return _t("No apps or menus match");
        }
        return _t("%(apps)s apps and %(menus)s menus match", {
            apps: appCount,
            menus: menuCount,
        });
    }
}
