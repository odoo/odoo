// @ts-check
/** @odoo-module native */

import { normalize } from "@web/core/l10n/utils";

/** @typedef {{childrenTree: MenuTreeNode[], actionPath?: string, actionID?: number | string, [key: string]: any}} MenuTreeNode */

/**
 * @param {MenuTreeNode} tree
 * @param {(node: MenuTreeNode, parents: MenuTreeNode[]) => void} cb
 * @param {MenuTreeNode[]} [parents]
 */
function traverseMenuTree(tree, cb, parents = []) {
    cb(tree, parents);
    tree.childrenTree.forEach((c) => traverseMenuTree(c, cb, [...parents, tree]));
}

/**
 * @param {{ actionPath?: string, actionID?: number|string }} menu
 * @returns {string}
 */
export function menuHref(menu) {
    return `/odoo/${menu.actionPath || `action-${menu.actionID}`}`;
}

/**
 * @typedef MenuEntry
 * @property {string} parents
 * @property {string} label
 * @property {number} id
 * @property {string} [xmlid]
 * @property {number|string} [actionID]
 * @property {string} href
 * @property {number} [appID]
 * @property {string} [module]
 * @property {string[]} [models]
 * @property {string} [category]
 * @property {number} [categorySequence]
 * @property {string[]} [keywords]
 * @property {string[]} [searchTerms]
 * @property {string} [webIconData]
 * @property {{ iconClass: string, color: string, backgroundColor: string }} [webIcon]
 */

/**
 * @typedef {MenuEntry & {
 *  actionID: number|string,
 *  appID: number,
 *  href: string,
 *  id: number,
 *  label: string,
 *  parents: string,
 * }} AppEntry
 */

const MAX_APPS_PER_SEARCHABLE_MODEL = 1;

/**
 * @param {AppEntry} app
 * @param {Map<string, number>} appsByModel
 * @returns {string[]}
 */
function appSearchTerms(app, appsByModel) {
    const terms = [...(app.keywords || [])];
    if (app.module) {
        terms.push(app.module);
    }
    for (const model of app.models || []) {
        if ((appsByModel.get(model) || 0) <= MAX_APPS_PER_SEARCHABLE_MODEL) {
            terms.push(model);
        }
    }
    return terms;
}

/**
 * @param {Object} menuTree
 * @returns {{ apps: AppEntry[], menuItems: MenuEntry[] }}
 */
export function computeAppsAndMenuItems(menuTree) {
    /** @type {AppEntry[]} */
    const apps = [];
    /** @type {MenuEntry[]} */
    const menuItems = [];
    /** @type {Map<number, Set<string>>} */
    const modelsByApp = new Map();
    /** @type {Map<string, number>} */
    const appsByModel = new Map();
    traverseMenuTree(/** @type {MenuTreeNode} */ (menuTree), (menuItem, parents) => {
        if (menuItem.actionResModel && menuItem.appID) {
            let models = modelsByApp.get(menuItem.appID);
            if (!models) {
                models = new Set();
                modelsByApp.set(menuItem.appID, models);
            }
            if (!models.has(menuItem.actionResModel)) {
                models.add(menuItem.actionResModel);
                appsByModel.set(
                    menuItem.actionResModel,
                    (appsByModel.get(menuItem.actionResModel) || 0) + 1,
                );
            }
        }
        if (!menuItem.id || !menuItem.actionID) {
            return;
        }
        const isApp = menuItem.id === menuItem.appID;
        /** @type {AppEntry} */
        const item = {
            parents: parents
                .slice(1)
                .map((p) => p.name)
                .join(" / "),
            label: menuItem.name,
            id: menuItem.id,
            xmlid: menuItem.xmlid,
            actionID: menuItem.actionID,
            href: menuHref(menuItem),
            appID: menuItem.appID,
        };
        if (!isApp) {
            menuItems.push(item);
            return;
        }
        const iconParts =
            typeof menuItem.webIcon === "string" ? menuItem.webIcon.split(",") : [];
        const module =
            typeof menuItem.xmlid === "string" && menuItem.xmlid.includes(".")
                ? menuItem.xmlid.split(".")[0]
                : undefined;
        if (module || (iconParts.length === 2 && iconParts[0])) {
            item.module = module || iconParts[0];
        }
        if (menuItem.webCategory) {
            item.category = menuItem.webCategory;
            item.categorySequence = menuItem.webCategorySequence || 0;
        }
        if (menuItem.webKeywords) {
            item.keywords = menuItem.webKeywords
                .split(",")
                .map((/** @type {string} */ word) => word.trim())
                .filter(Boolean);
        }
        if (menuItem.webIconData) {
            item.webIconData = menuItem.webIconData;
        } else {
            const [iconClass, color, backgroundColor] = (menuItem.webIcon || "").split(
                ",",
            );
            if (backgroundColor !== undefined) {
                item.webIcon = { iconClass, color, backgroundColor };
            } else {
                item.webIconData = "/web/static/img/default_icon_app.png";
            }
        }
        apps.push(item);
    });
    for (const app of apps) {
        app.models = [...(modelsByApp.get(/** @type {number} */ (app.appID)) || [])];
        app.searchTerms = appSearchTerms(app, appsByModel);
    }
    return { apps, menuItems };
}

/** @type {WeakMap<Object, { apps: AppEntry[], menuItems: MenuEntry[] }>} */
const flattenedTrees = new WeakMap();

/**
 * @param {Object} menuTree
 * @returns {{ apps: AppEntry[], menuItems: MenuEntry[] }}
 */
export function flattenMenuTree(menuTree) {
    let flattened = flattenedTrees.get(menuTree);
    if (!flattened) {
        flattened = computeAppsAndMenuItems(menuTree);
        flattenedTrees.set(menuTree, flattened);
    }
    return flattened;
}

/** @type {WeakMap<object, string>} */
const searchKeys = new WeakMap();

/**
 * @param {{ parents: string, label: string }} menu
 * @returns {string}
 */
export function menuSearchKey(menu) {
    let key = searchKeys.get(menu);
    if (key === undefined) {
        key = normalize(
            `${menu.parents} / ${menu.label}`.split("/").reverse().join("/"),
        );
        searchKeys.set(menu, key);
    }
    return key;
}

/** @type {WeakMap<object, string[]>} */
const appSearchKeys = new WeakMap();

/**
 * @param {{ label: string, searchTerms?: string[] }} app
 * @returns {string[]}
 */
export function appSearchKey(app) {
    let keys = appSearchKeys.get(app);
    if (keys === undefined) {
        keys = [app.label, ...(app.searchTerms || [])].map(normalize);
        appSearchKeys.set(app, keys);
    }
    return keys;
}

/**
 * @param {{ xmlid?: string }[]} apps
 * @param {string[]} order
 */
export function reorderApps(apps, order) {
    const ranks = new Map();
    for (const [index, xmlid] of order.entries()) {
        if (!ranks.has(xmlid)) {
            ranks.set(xmlid, index);
        }
    }
    apps.sort((a, b) => {
        const aIndex = ranks.get(a.xmlid) ?? -1;
        const bIndex = ranks.get(b.xmlid) ?? -1;
        if (aIndex === -1 && bIndex === -1) {
            return 0;
        }
        if (aIndex === -1) {
            return -1;
        }
        if (bIndex === -1) {
            return 1;
        }
        return aIndex - bIndex;
    });
}

const HOME_MENU_CONFIG_VERSION = 2;

/**
 * @typedef HomeMenuConfig
 * @property {string[]} order
 * @property {string[]} pinned
 * @property {string[]} hidden
 */

/** @param {unknown} list */
function xmlids(list) {
    return Array.isArray(list)
        ? [...new Set(list.filter((item) => typeof item === "string" && item))]
        : [];
}

/**
 * @param {unknown} raw
 * @returns {HomeMenuConfig | null}
 */
export function readHomeMenuConfig(raw) {
    let value = raw;
    if (typeof raw === "string") {
        try {
            value = JSON.parse(raw);
        } catch {
            value = null;
        }
    }
    if (Array.isArray(value)) {
        return { order: xmlids(value), pinned: [], hidden: [] };
    }
    if (
        value &&
        typeof value === "object" &&
        (!Object.hasOwn(value, "version") ||
            /** @type {Record<string, unknown>} */ (value).version ===
                HOME_MENU_CONFIG_VERSION)
    ) {
        const config = /** @type {Record<string, unknown>} */ (value);
        const hidden = xmlids(config.hidden);
        const hiddenIds = new Set(hidden);
        return {
            order: xmlids(config.order),
            pinned: xmlids(config.pinned).filter((id) => !hiddenIds.has(id)),
            hidden,
        };
    }
    return null;
}

/**
 * @param {unknown} raw
 * @returns {HomeMenuConfig}
 */
export function parseHomeMenuConfig(raw) {
    return readHomeMenuConfig(raw) ?? { order: [], pinned: [], hidden: [] };
}

/**
 * @param {HomeMenuConfig} config
 * @returns {string}
 */
export function serializeHomeMenuConfig(config) {
    return JSON.stringify({
        version: HOME_MENU_CONFIG_VERSION,
        order: [...config.order],
        pinned: [...config.pinned],
        hidden: [...config.hidden],
    });
}

/**
 * @param {HomeMenuConfig} config
 * @returns {boolean}
 */
export function isDefaultHomeMenuConfig(config) {
    return !config.order.length && !config.pinned.length && !config.hidden.length;
}
