// @ts-check
/** @odoo-module native */

import { onMounted, onWillUnmount, useExternalListener } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { UserEvent } from "@web/core/events";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { user, userBus } from "@web/core/user";

const badgeProviders = registry.category("home_menu_badges");
badgeProviders.addValidation({
    provide: Function,
    subscribe: { type: Function, optional: true },
    timeoutMs: { type: Number, optional: true },
});
const BADGE_TTL = 20_000;
/** @typedef {{ xmlid?: string, module?: string, models?: string[] }} BadgeApp */
/** @type {WeakMap<object, {key: string, at: number, badges: Promise<Record<string, number>>}>} */
let cache = new WeakMap();

/** @param {import("@web/env").OdooEnv} [env] */
export function invalidateHomeMenuBadges(env) {
    if (env) {
        cache.delete(env.services ?? env);
    } else {
        cache = new WeakMap();
    }
}
badgeProviders.addEventListener("UPDATE", () => invalidateHomeMenuBadges());

/**
 * @param {import("@web/env").OdooEnv} env
 * @param {() => void} onChange
 */
export function useHomeMenuBadgeUpdates(env, onChange) {
    /** @type {(() => void)[]} */
    let stops = [];
    const stopAll = () => {
        for (const stop of stops) {
            try {
                stop();
            } catch (error) {
                console.warn("Home menu badge subscription cleanup failed", error);
            }
        }
        stops = [];
    };
    const subscribe = () => {
        stopAll();
        for (const provider of badgeProviders.getAll()) {
            if (provider.subscribe) {
                try {
                    const stop = provider.subscribe(env, () => {
                        invalidateHomeMenuBadges(env);
                        onChange();
                    });
                    if (typeof stop === "function") {
                        stops.push(stop);
                    }
                } catch (error) {
                    console.warn("Home menu badge subscription failed", error);
                }
            }
        }
    };
    onMounted(subscribe);
    useExternalListener(userBus, UserEvent.ACTIVE_COMPANIES_CHANGED, () => {
        invalidateHomeMenuBadges(env);
        onChange();
    });
    useExternalListener(badgeProviders, "UPDATE", () => {
        subscribe();
        onChange();
    });
    onWillUnmount(stopAll);
}

/**
 * @param {import("@web/env").OdooEnv} env
 * @param {BadgeApp[]} apps
 * @param {{ refresh?: boolean }} [options]
 * @returns {Promise<Record<string, number>>}
 */
export function loadHomeMenuBadges(env, apps, { refresh = false } = {}) {
    const catalog = [...apps].sort((a, b) =>
        (a.xmlid ?? "").localeCompare(b.xmlid ?? ""),
    );
    const key = JSON.stringify([
        user.activeCompanies.map(({ id }) => id),
        catalog.map(({ xmlid, module, models }) => [xmlid, module, models]),
    ]);
    const owner = env.services ?? env;
    const previous = cache.get(owner);
    const now = Date.now();
    if (!refresh && previous?.key === key && now - previous.at < BADGE_TTL) {
        return previous.badges;
    }
    const badges = countHomeMenuBadges(env, catalog);
    cache.set(owner, { key, at: now, badges });
    return badges;
}

/**
 * @param {any} provider
 * @param {import("@web/env").OdooEnv} env
 * @param {BadgeApp[]} apps
 */
async function runProvider(provider, env, apps) {
    let timer;
    const timeoutMs =
        Number.isFinite(provider.timeoutMs) && provider.timeoutMs > 0
            ? Math.min(provider.timeoutMs, 5000)
            : 5000;
    try {
        return await Promise.race([
            Promise.resolve().then(() => provider.provide(env, apps)),
            new Promise((_, reject) => {
                timer = browser.setTimeout(
                    () => reject(new Error("Home menu badge provider timed out")),
                    timeoutMs,
                );
            }),
        ]);
    } finally {
        browser.clearTimeout(timer);
    }
}

/**
 * @param {import("@web/env").OdooEnv} env
 * @param {BadgeApp[]} apps
 */
async function countHomeMenuBadges(env, apps) {
    /** @type {Record<string, number>} */
    const badges = {};
    const settled = await Promise.allSettled(
        badgeProviders.getAll().map((provider) => runProvider(provider, env, apps)),
    );
    for (const result of settled) {
        if (result.status === "rejected") {
            console.warn("Home menu badge provider failed", result.reason);
            continue;
        }
        if (
            !result.value ||
            typeof result.value !== "object" ||
            Array.isArray(result.value)
        ) {
            continue;
        }
        for (const [xmlid, value] of Object.entries(result.value)) {
            const count = Number(value);
            if (Number.isSafeInteger(count) && count > 0) {
                badges[xmlid] = Math.min(
                    Number.MAX_SAFE_INTEGER,
                    (badges[xmlid] || 0) + count,
                );
            }
        }
    }
    return badges;
}

const BADGE_CEILING = 99;

/**
 * @param {Record<string, number>} badges
 * @param {{ xmlid?: string }} app
 * @returns {{ count: number, text: string, label: string }}
 */
export function appBadge(badges, app) {
    const count = app.xmlid === undefined ? 0 : badges[app.xmlid] || 0;
    return {
        count,
        text: count > BADGE_CEILING ? `${BADGE_CEILING}+` : String(count),
        label: _t("%s pending", count),
    };
}
