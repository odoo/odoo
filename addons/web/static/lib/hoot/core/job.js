/** @odoo-module */

import { HootError, generateHash, isOfType, normalize } from "../hoot_utils";
import { createTags } from "./tag";

/**
 * @typedef {{
 *  multi?: number;
 *  skip?: boolean;
 *  tags?: string[];
 *  timeout?: number;
 *  todo?: boolean;
 * }} JobConfig
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {JobConfig} config
 */
const validateConfig = (config) => {
    for (const [key, value] of Object.entries(config)) {
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
    tags: "string[]",
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
    /** @type {Set<string>} */
    tagNames = new Set();
    /** @type {import("./tag").Tag[]} */
    tags = [];
    visited = 0;

    /**
     * @param {import("./suite").Suite | null} parent
     * @param {string} name
     * @param {JobConfig} config
     */
    constructor(parent, name, config) {
        this.parent = parent || null;
        this.name = name;

        if (this.parent) {
            // Assigns parent path and config
            Object.assign(this.config, this.parent.config);
            this.path.unshift(...this.parent.path);
        }

        // Assigns and validates job config
        Object.assign(this.config, config);
        validateConfig(this.config);

        this.fullName = this.path.map((job) => job.name).join("/");
        this.id = generateHash(this.fullName);
        this.key = normalize(this.fullName);

        // Tags
        const tags = createTags(this.parent?.tags, config.tags);
        for (const tag of tags) {
            this.tags.push(tag);
            this.tagNames.add(normalize(tag.name));
        }
        delete this.config.tags;
    }

    /**
     * @returns {boolean}
     */
    canRun() {
        return !this.config.skip;
    }
}
