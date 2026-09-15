// @ts-check
/** @odoo-module native */

import { App } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { makeAssetLog } from "@web/core/utils/asset_log";
import { cyrb53 } from "@web/core/utils/format/strings";
import { IndexedDB } from "@web/core/utils/indexed_db";
import { session } from "@web/session";

/**
 * @typedef {(app: any, bdom: any, helpers: any) => Function} TemplateFn
 */

const log = makeAssetLog("template_cache");

const TABLE = "compiled";
const FN_ARGS = "app, bdom, helpers";

/**
 * @param {string | Element} template
 * @returns {string}
 */
function templateSource(template) {
    return typeof template === "string" ? template : template.outerHTML;
}

/**
 * @param {Function} fn
 * @returns {string}
 */
function functionBody(fn) {
    const source = fn.toString();
    return source.slice(source.indexOf("{") + 1, source.lastIndexOf("}"));
}

export class TemplateCompileCache {
    /**
     * @param {{
     *  db?: { readAll(table: string): Promise<Record<string, string>>, write(table: string, key: string, value: string): Promise<any> } | null,
     *  scope: string,
     * }} config
     */
    constructor({ db, scope }) {
        this.db = db ?? null;
        this.scope = scope;
        /** @type {Map<string, string>} */
        this.code = new Map();
        this.hits = 0;
        this.misses = 0;
        this.ready = this._load();
    }

    async _load() {
        if (!this.db) {
            return;
        }
        try {
            const stored = await this.db.readAll(TABLE);
            for (const [key, code] of Object.entries(stored)) {
                if (key.startsWith(this.scope) && typeof code === "string") {
                    this.code.set(key, code);
                }
            }
            log("loaded", `entries=${this.code.size}`, `scope=${this.scope}`);
        } catch (error) {
            log("load failed, compiling for this session", error);
        }
    }

    /**
     * @param {string | Element} template
     * @returns {string}
     */
    key(template) {
        const source = templateSource(template);
        return `${this.scope}/${source.length}-${cyrb53(source)}`;
    }

    /**
     * @param {string} key
     * @returns {TemplateFn | null}
     */
    lookup(key) {
        const code = this.code.get(key);
        if (code === undefined) {
            this.misses++;
            return null;
        }
        this.hits++;
        return /** @type {TemplateFn} */ (new Function(FN_ARGS, code));
    }

    /**
     * The pre-seed seam: what a server that compiles ahead of time would
     * call, and what a miss calls after compiling.
     *
     * @param {string} key
     * @param {string} code
     * @param {{ persist?: boolean }} [options]
     */
    seed(key, code, { persist = true } = {}) {
        this.code.set(key, code);
        if (persist && this.db) {
            this.db.write(TABLE, key, code).catch((error) => {
                log("write failed", error);
            });
        }
    }

    /**
     * @param {string} key
     * @param {Function} fn
     */
    store(key, fn) {
        this.seed(key, functionBody(fn));
    }

    /**
     * Route an OWL app's template compiles through the cache: a hit returns
     * the stored code as a template function, a miss compiles and stores.
     *
     * @param {{ _compileTemplate: (name: string, template: string | Element) => TemplateFn, dev?: boolean }} app
     */
    install(app) {
        const compile = app._compileTemplate;
        app._compileTemplate = (name, template) => {
            const key = this.key(template);
            const cached = this.lookup(key);
            if (cached) {
                return cached;
            }
            const fn = compile.call(app, name, template);
            this.store(key, fn);
            return fn;
        };
    }
}

/**
 * Everything the compiled code is a function of besides the template text:
 * the translations it embeds, OWL's compiler, the assets that shipped the
 * template — the last two through the registry hash that versions the
 * database.
 *
 * @param {{ translationsHash?: string, code: string }} localization
 * @param {string} owlVersion
 */
export function cacheScope(localization, owlVersion) {
    return `${owlVersion}/${localization.code}/${localization.translationsHash || "-"}`;
}

export const templateCompileCacheService = {
    dependencies: ["localization"],
    /**
     * @param {any} env
     * @param {{ localization: any }} services
     */
    async start(env, { localization }) {
        const db = session.registry_hash
            ? new IndexedDB("template_compile_cache", session.registry_hash)
            : null;
        const cache = new TemplateCompileCache({
            db,
            scope: cacheScope(localization, /** @type {any} */ (App).version),
        });
        await cache.ready;
        return cache;
    },
};

registry
    .category("services")
    .add("template_compile_cache", templateCompileCacheService);
