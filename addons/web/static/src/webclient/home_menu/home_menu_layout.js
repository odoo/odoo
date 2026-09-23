// @ts-check
/** @odoo-module native */

import { onWillUnmount, reactive, useExternalListener } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";
import { Mutex } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import {
    parseHomeMenuConfig,
    readHomeMenuConfig,
    serializeHomeMenuConfig,
} from "@web/webclient/menus/menu_utils";

/**
 * @template {{ xmlid?: string }} T
 * @param {import("@web/webclient/menus/menu_utils").HomeMenuConfig} config
 * @param {T[]} apps
 * @returns {T[]}
 */
export function shownApps(config, apps) {
    return apps.filter(
        (app) => app.xmlid === undefined || !config.hidden.includes(app.xmlid),
    );
}

/**
 * @template {{ xmlid?: string }} T
 * @param {import("@web/webclient/menus/menu_utils").HomeMenuConfig} config
 * @param {T[]} apps
 * @returns {T[]}
 */
export function pinnedApps(config, apps) {
    const byXmlid = new Map(
        apps.flatMap((app) => (app.xmlid === undefined ? [] : [[app.xmlid, app]])),
    );
    return config.pinned.flatMap((xmlid) => {
        const app = byXmlid.get(xmlid);
        return app ? [app] : [];
    });
}

/**
 * @param {string[]} order
 * @param {string} movedId
 * @param {string} [afterId]
 * @returns {string[] | null}
 */
export function orderAfterDrag(order, movedId, afterId) {
    const from = order.indexOf(movedId);
    if (from === -1) {
        return null;
    }
    const next = [...order];
    next.splice(from, 1);
    next.splice(afterId ? next.indexOf(afterId) + 1 : 0, 0, movedId);
    return next;
}

export function homeMenuLayoutStorageKey() {
    return `webclient_home_layout:${session.db}:${user.userId}`;
}

/** @param {() => void} onChange */
export function useHomeMenuLayoutSync(onChange) {
    const orm = useService("orm");
    let generation = 0;
    onWillUnmount(() => {
        generation++;
    });
    useExternalListener(window, "storage", async (event) => {
        if (event.key !== homeMenuLayoutStorageKey() || !event.newValue) {
            return;
        }
        const request = ++generation;
        try {
            const [settings] = await orm.read(
                "res.users.settings",
                [user.settings.id],
                ["homemenu_config"],
            );
            if (request !== generation) {
                return;
            }
            user.updateUserSettings("homemenu_config", settings.homemenu_config);
            onChange();
        } catch {}
    });
}

/** @typedef {{ operation: string, xmlid?: string, value?: boolean | string[] }} LayoutChange */

export class HomeMenuLayout {
    /**
     * @param {{
     * config: import("@web/webclient/menus/menu_utils").HomeMenuConfig,
     * defaultConfig: import("@web/webclient/menus/menu_utils").HomeMenuConfig,
     * orm: import("services").ServiceFactories["orm"],
     * personal?: boolean,
     * onSaved?: () => void,
     * }} params
     */
    constructor({ config, defaultConfig, orm, personal, onSaved = () => {} }) {
        this.orm = orm;
        this.onSaved = onSaved;
        this.mutex = new Mutex();
        /** @type {LayoutChange[]} */
        this.pending = [];
        this.state = reactive({
            status: "saved",
            config,
            defaultConfig,
            personal:
                personal ??
                serializeHomeMenuConfig(config) !==
                    serializeHomeMenuConfig(defaultConfig),
        });
    }

    /** @returns {import("@web/webclient/menus/menu_utils").HomeMenuConfig} */
    get config() {
        return this.state.config;
    }

    set config(config) {
        this.state.config = config;
    }

    /** @returns {import("@web/webclient/menus/menu_utils").HomeMenuConfig} */
    get defaultConfig() {
        return this.state.defaultConfig;
    }

    set defaultConfig(config) {
        this.state.defaultConfig = config;
    }

    get unsaved() {
        return this.pending.length > 0 || this.state.status === "saving";
    }

    /** @param {import("@web/webclient/menus/menu_utils").HomeMenuConfig} config */
    setConfig(config) {
        if (!this.unsaved) {
            this.config = config;
            this.state.personal =
                readHomeMenuConfig(user.settings?.homemenu_config) !== null;
        }
    }

    /** @param {{ xmlid?: string }} app */
    isPinned(app) {
        return app.xmlid !== undefined && this.config.pinned.includes(app.xmlid);
    }

    /** @param {{ xmlid?: string }} app */
    isHidden(app) {
        return app.xmlid !== undefined && this.config.hidden.includes(app.xmlid);
    }

    get isCustomised() {
        return (
            serializeHomeMenuConfig(this.config) !==
            serializeHomeMenuConfig(this.defaultConfig)
        );
    }

    get canReset() {
        return this.state.personal || this.isCustomised;
    }

    get canSetCompanyDefault() {
        return user.isAdmin;
    }

    /** @param {LayoutChange} change */
    apply(change) {
        const { operation, xmlid, value } = change;
        if (operation === "reset") {
            Object.assign(this.config, parseHomeMenuConfig(this.defaultConfig));
            this.state.personal = false;
            return;
        }
        this.state.personal = true;
        if (operation === "order" || operation === "pinned_order") {
            const key = operation === "order" ? "order" : "pinned";
            const requested = [...new Set(/** @type {string[]} */ (value))].filter(
                (id) => key === "order" || this.config.pinned.includes(id),
            );
            this.config[key] = [
                ...requested,
                ...this.config[key].filter((id) => !requested.includes(id)),
            ];
        } else if (xmlid) {
            const key = operation === "pin" ? "pinned" : "hidden";
            if (!value) {
                this.config[key] = this.config[key].filter((id) => id !== xmlid);
            }
            if (value) {
                if (!this.config[key].includes(xmlid)) {
                    this.config[key].push(xmlid);
                }
                const other = key === "pinned" ? "hidden" : "pinned";
                this.config[other] = this.config[other].filter((id) => id !== xmlid);
            }
        }
    }

    /** @param {LayoutChange} change */
    queue(change) {
        this.apply(change);
        this.pending.push(change);
        return this.persist();
    }

    /** @param {{ xmlid?: string }} app */
    togglePinned(app) {
        if (app.xmlid) {
            return this.queue({
                operation: "pin",
                xmlid: app.xmlid,
                value: !this.isPinned(app),
            });
        }
    }

    /** @param {{ xmlid?: string }} app */
    toggleHidden(app) {
        if (app.xmlid) {
            return this.queue({
                operation: "hide",
                xmlid: app.xmlid,
                value: !this.isHidden(app),
            });
        }
    }

    /** @param {string[]} order */
    setOrder(order) {
        return this.queue({ operation: "order", value: order });
    }

    /** @param {string[]} order */
    setPinnedOrder(order) {
        return this.queue({ operation: "pinned_order", value: order });
    }

    reset() {
        return {
            order: this.defaultConfig.order,
            saved: this.queue({ operation: "reset" }),
        };
    }

    async flush() {
        do {
            await this.persist();
        } while (this.unsaved);
    }

    // A refusal is already on screen as "Changes could not be saved"; failing
    // the leave on top of it would keep the user on the home menu for good.
    async flushBeforeLeave() {
        try {
            await this.flush();
        } catch (error) {
            if (this.state.status !== "error") {
                throw error;
            }
        }
    }

    async setCompanyDefault() {
        await this.flush();
        const config = JSON.parse(serializeHomeMenuConfig(this.config));
        await this.orm.write("res.company", [user.activeCompany.id], {
            homemenu_default_config: config,
        });
        session.homemenu_default_config = config;
        this.defaultConfig = parseHomeMenuConfig(config);
    }

    persist() {
        return this.mutex.exec(async () => {
            if (!this.pending.length) {
                return;
            }
            const changes = this.pending.splice(0);
            this.state.status = "saving";
            try {
                const settings = await this.orm.call(
                    "res.users.settings",
                    "update_homemenu_config",
                    [[user.settings.id], changes],
                );
                const raw = settings.homemenu_config;
                user.updateUserSettings("homemenu_config", raw);
                Object.assign(
                    this.config,
                    readHomeMenuConfig(raw) ?? parseHomeMenuConfig(this.defaultConfig),
                );
                this.state.personal = readHomeMenuConfig(raw) !== null;
                for (const change of this.pending) {
                    this.apply(change);
                }
                this.state.status = this.pending.length ? "saving" : "saved";
                try {
                    browser.localStorage.setItem(
                        homeMenuLayoutStorageKey(),
                        JSON.stringify({ config: raw, at: Date.now() }),
                    );
                } catch {}
            } catch (error) {
                this.pending.unshift(...changes);
                this.state.status = "error";
                throw error;
            }
            this.onSaved();
        });
    }
}
