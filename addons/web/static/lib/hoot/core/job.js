/** @odoo-module */

import { HootError, generateHash, isOfType, normalize } from "../hoot_utils";
import { Tag } from "./tag";

/**
 * @typedef {{
 *  debug?: boolean;
 *  multi?: number;
 *  only?: boolean;
 *  skip?: boolean;
 *  tags?: string[];
 *  timeout?: number;
 *  todo?: boolean;
 * }} JobConfig
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Object: { assign: $assign, entries: $entries },
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {JobConfig} config
 */
const validateConfig = (config) => {
    for (const [key, value] of $entries(config)) {
        if (!isOfType(value, CONFIG_TAG_SCHEMA[key])) {
            throw new HootError(`invalid config tag: parameter "${key}" does not exist`);
        }
    }
};

/** @type {Record<keyof JobConfig, import("../hoot_utils").ArgumentType>} */
const CONFIG_TAG_SCHEMA = {
    debug: "boolean",
    multi: "integer",
    only: "boolean",
    skip: "boolean",
    timeout: "number",
    todo: "boolean",
};

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class Job {
    /** @type {JobConfig} */
    config = {};
    /** @type {Job[]} */
    path = [this];
    /** @type {Tag[]} */
    tags = [];
    visited = 0;

    /**
     * @param {import("./suite").Suite | null} parent
     * @param {string} name
     * @param {JobConfig & { tags?: Iterable<Tag | string> }} config
     */
    constructor(parent, name, config) {
        this.parent = parent || null;
        this.name = name;

        if (this.parent) {
            // Assigns parent path and config
            this.configure({
                ...this.parent.config,
                tags: this.parent.tags,
            });
            this.path.unshift(...this.parent.path);
        }

        this.fullName = this.path.map((job) => job.name).join("/");
        this.id = generateHash(this.fullName);
        this.key = normalize(this.fullName);

        this.configure(config);
    }

    /**
     * @returns {boolean}
     */
    canRun() {
        return !this.config.skip;
    }

    /**
     * @param {JobConfig & { tags?: Iterable<Tag | string> }} config
     */
    configure({ tags, ...config }) {
        // Assigns and validates job config
        $assign(this.config, config);
        validateConfig(this.config);

        // Tags
        for (const tag of Tag.getAll(tags)) {
            if (!this.tags.includes(tag)) {
                this.tags.push(tag);
                tag.weight++;
            }
        }
    }
}
