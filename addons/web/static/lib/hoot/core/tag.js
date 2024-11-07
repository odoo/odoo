/** @odoo-module */

import { isIterable } from "@web/../lib/hoot-dom/hoot_dom_utils";
import { HootError, levenshtein, normalize, stringToNumber } from "../hoot_utils";

/**
 * @typedef {import("./suite").Suite} Suite
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Math: { ceil: $ceil, max: $max },
    Object: { create: $create, keys: $keys },
    Set,
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * Checks for similarity with other existing tag names.
 *
 * A tag name is considered similar to another if the following conditions are met:
 * - it doesn't include numbers (the number is likely meaningful enough to dissociate
 *   it from other similar tags);
 * - the edit distance between the 2 is <= 10% of the length of the largest string
 *
 * @param {string} tagName
 */
const checkTagSimilarity = (tagName) => {
    if (R_UNIQUE_TAG.test(tagName)) {
        return;
    }
    for (const name of $keys(existingTags)) {
        if (R_UNIQUE_TAG.test(name)) {
            continue;
        }
        const maxLength = $max(tagName.length, name.length);
        const threshold = $ceil(SIMILARITY_PERCENTAGE * maxLength);
        const editDistance = levenshtein(name, tagName, { normalize: true });
        if (editDistance <= threshold) {
            similarities.push([name, tagName]);
        }
    }
};

const R_UNIQUE_TAG = /\d/;
const SIMILARITY_PERCENTAGE = 0.1;
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
const existingTags = $create(null);
/** @type {[string, string][]} */
const similarities = [];
let canCreateTag = false;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function getTagSimilarities() {
    return similarities;
}

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
        const tagName = String(tagSpec).trim();
        if (!existingTags[tagName]) {
            checkTagSimilarity(tagName);

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
