/** @odoo-module */

import { isIterable } from "@web/../lib/hoot-dom/hoot_dom_utils";
import { HootError, normalize, stringToNumber } from "../hoot_utils";

/**
 * @typedef {import("./suite").Suite} Suite
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Set } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const TAG_COLORS = [
    ["#f97316", "#ffedd5"], // orange
    ["#eab308", "#fef9c3"], // yellow
    ["#84cc16", "#ecfccb"], // lime
    ["#10b981", "#d1fae5"], // emerald
    ["#06b6d4", "#cffafe"], // cyan
    ["#3b82f6", "#dbeafe"], // blue
    ["#6366f1", "#e0e7ff"], // indigo
    ["#d946ef", "#fae8ff"], // fuschia
    ["#f43f5e", "#ffe4e6"], // rose
];

/** @type {Record<string, Tag>} */
const existingTags = {};
let canCreateTag = false;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Cannot be instantiated outside of {@link Tag.get}.
 * @see {@link Tag.get}
 */
export class Tag {
    static DEBUG = "debug";
    static ONLY = "only";
    static SKIP = "skip";
    static TODO = "todo";

    weight = 0;

    /**
     * @param {string} name
     */
    constructor(name) {
        if (!canCreateTag) {
            throw new HootError(`illegal constructor: use \`createTag("${name}")\` instead`);
        }

        this.name = name;
        this.id = this.name;
        this.key = normalize(this.name);

        this.color = TAG_COLORS[stringToNumber(this.key) % TAG_COLORS.length];
    }

    /**
     * @param {Tag | string} tagSpec
     * @returns {Tag}
     */
    static get(tagSpec) {
        if (tagSpec instanceof this) {
            return tagSpec;
        }
        const tagName = String(tagSpec);
        if (!existingTags[tagName]) {
            canCreateTag = true;
            existingTags[tagName] = new this(tagName);
            canCreateTag = false;
        }
        return existingTags[tagName];
    }

    /**
     * @param {Iterable<Tag | string>} [tagSpecs]
     * @returns {Set<Tag>}
     */
    static getAll(tagSpecs) {
        /** @type {Set<Tag>} */
        const tags = new Set();
        if (isIterable(tagSpecs)) {
            for (const tagSpec of tagSpecs) {
                tags.add(this.get(tagSpec));
            }
        }
        return tags;
    }
}
