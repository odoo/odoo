/** @odoo-module */

import { generateHash, HootError, isOfType, normalize } from "../hoot_utils";
import { applyTags } from "./tag";

/**
 * @typedef {{
 *  debug?: boolean;
 *  multi?: number;
 *  only?: boolean;
 *  skip?: boolean;
 *  timeout?: number;
 *  todo?: boolean;
 * }} JobConfig
 *
 * @typedef {import("./tag").Tag} Tag
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Object: { assign: $assign, entries: $entries },
    Symbol,
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {JobConfig} config
 */
function validateConfig(config) {
    for (const [key, value] of $entries(config)) {
        if (!isOfType(value, CONFIG_TAG_SCHEMA[key])) {
            throw new HootError(`invalid config tag: parameter "${key}" does not exist`);
        }
    }
}

/** @type {Record<keyof JobConfig, import("../hoot_utils").ArgumentType>} */
const CONFIG_TAG_SCHEMA = {
    debug: "boolean",
    multi: "number",
    only: "boolean",
    skip: "boolean",
    timeout: "number",
    todo: "boolean",
};

const S_MINIMIZED = Symbol("minimized");

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class Job {
    /** @type {JobConfig} */
    config = {};
    /** @type {Job[]} */
    path = [this];
    runCount = 0;
    /** @type {Tag[]} */
    tags = [];

    get isMinimized() {
        return S_MINIMIZED in this;
    }

    /**
     * @param {import("./suite").Suite | null} parent
     * @param {string} name
     * @param {JobConfig & { tags?: Iterable<Tag> }} config
     */
    constructor(parent, name, config) {
        this.parent = parent || null;
        this.name = name;

        if (this.parent) {
            // Assigns parent path and config (ignoring multi)
            const parentConfig = {
                ...this.parent.config,
                tags: this.parent.tags,
            };
            delete parentConfig.multi;
            this.configure(parentConfig);
            this.path.unshift(...this.parent.path);
        }

        this.fullName = this.path.map((job) => job.name).join("/");
        this.id = generateHash(this.fullName);
        this.key = normalize(this.fullName);

        this.configure(config);
    }

    after() {
        for (const tag of this.tags) {
            tag.after?.(this);
        }
    }

    before() {
        for (const tag of this.tags) {
            tag.before?.(this);
        }
    }

    /**
     * @param {JobConfig & { tags?: Iterable<Tag> }} config
     */
    configure({ tags, ...config }) {
        // Assigns and validates job config
        $assign(this.config, config);
        validateConfig(this.config);

        // Add tags
        applyTags(this, tags);
    }

    minimize() {
        this[S_MINIMIZED] = true;
    }

    /**
     * @returns {boolean}
     */
    willRunAgain() {
        return this.runCount < (this.config.multi || 0) || this.parent?.willRunAgain();
    }
}
