// @ts-check
/** @odoo-module native */

import { EventBus, reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

import { ProfilingItem } from "./profiling_item.js";
import { profilingSystrayItem } from "./profiling_systray_item.js";

const systrayRegistry = registry.category("systray");

class ProfilingService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{ action: any, orm: any, lazy_session: any }} services
     */
    constructor(env, { action, orm, lazy_session }) {
        this.env = env;
        this.action = action;
        this.orm = orm;
        this.lazy_session = lazy_session;
        this.bus = new EventBus();
        this.stateGeneration = 0;
        this.pendingMutation = Promise.resolve();

        const state = reactive(
            {
                session: false,
                collectors: ["sql", "traces_async"],
                params: {},
                get isEnabled() {
                    return Boolean(state.session);
                },
            },
            () => this.notify(),
        );
        this.state = state;

        this.loadLazyState("profile_session", "session");
        this.loadLazyState("profile_collectors", "collectors");
        this.loadLazyState("profile_params", "params");

        this.notify();
    }

    notify() {
        if (
            systrayRegistry.contains("web.profiling") &&
            this.state.isEnabled === false
        ) {
            systrayRegistry.remove("web.profiling");
        }
        if (
            !systrayRegistry.contains("web.profiling") &&
            this.state.isEnabled === true
        ) {
            systrayRegistry.add("web.profiling", profilingSystrayItem, {
                sequence: 99,
            });
        }
        this.bus.trigger("UPDATE");
    }

    /**
     * @param {string} sessionKey
     * @param {string} stateKey
     */
    async loadLazyState(sessionKey, stateKey) {
        const bootGeneration = this.stateGeneration;
        for (let attempt = 0; attempt < 2; attempt++) {
            try {
                const value = await this.lazy_session.getValue(sessionKey);
                if (value && this.stateGeneration === bootGeneration) {
                    /** @type {Record<string, any>} */ (this.state)[stateKey] = value;
                }
                return;
            } catch {}
        }
    }

    /** @param {Record<string, any> | (() => Record<string, any>)} params */
    setProfiling(params) {
        this.stateGeneration++;
        const operation = this.pendingMutation.then(async () => {
            const kwargs = {
                collectors: this.state.collectors,
                params: this.state.params,
                profile: this.state.isEnabled,
                ...(typeof params === "function" ? params() : params),
            };
            const resp = await this.orm.call("ir.profile", "set_profiling", [], kwargs);
            if (resp.type) {
                Promise.resolve(this.action.doAction(resp)).catch(console.warn);
            } else {
                this.state.session = resp.session;
                this.state.collectors = resp.collectors;
                this.state.params = resp.params;
            }
        });
        this.pendingMutation = operation.catch(() => {});
        return operation;
    }

    profilingItem() {
        return {
            type: "component",
            Component: ProfilingItem,
            props: { bus: this.bus },
            sequence: 570,
            section: "tools",
        };
    }

    async toggleProfiling() {
        await this.setProfiling(() => ({ profile: !this.state.isEnabled }));
    }

    /** @param {string} collector */
    async toggleCollector(collector) {
        await this.setProfiling(() => {
            const nextCollectors = this.state.collectors.slice();
            const index = nextCollectors.indexOf(collector);
            if (index >= 0) {
                nextCollectors.splice(index, 1);
            } else {
                nextCollectors.push(collector);
            }
            return { collectors: nextCollectors };
        });
    }

    /**
     * @param {string} key
     * @param {any} value
     */
    async setParam(key, value) {
        await this.setProfiling(() => ({
            params: { ...this.state.params, [key]: value },
        }));
    }

    /**
     * @param {string} collector
     * @returns {boolean}
     */
    isCollectorEnabled(collector) {
        return this.state.collectors.includes(collector);
    }
}

registry
    .category("debug")
    .category("default")
    .add(
        "profilingItem",
        /** @type {(params: { env: import("@web/env").OdooEnv }) => any} */ (
            ({ /** @type {any} */ env }) =>
                env.services.profiling?.profilingItem() ?? null
        ),
    );

const profilingService = {
    dependencies: ["action", "orm", "lazy_session"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{ action: any, orm: any, lazy_session: any }} services
     * @returns {ProfilingService | undefined}
     */
    start(env, services) {
        if (!env.debug) {
            return;
        }
        return new ProfilingService(env, services);
    },
};

registry.category("services").add("profiling", profilingService);
