/** @odoo-module */

import { HootError, levenshtein, normalize, stringify, stringToNumber } from "../hoot_utils";

/**
 * @typedef {import("./job").Job} Job
 * @typedef {import("./suite").Suite} Suite
 * @typedef {import("./suite").Test} Test
 *
 * @typedef {{
 *  name: string;
 *  exclude?: string[];
 *  before?: (test: Test) => any;
 *  after?: (test: Test) => any;
 * }} TagDefinition
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
 * @param {string} tagKey
 * @param {string} tagName
 */
const checkTagSimilarity = (tagKey, tagName) => {
    if (R_UNIQUE_TAG.test(tagKey)) {
        return;
    }
    for (const key of $keys(existingTags)) {
        if (R_UNIQUE_TAG.test(key)) {
            continue;
        }
        const maxLength = $max(tagKey.length, key.length);
        const threshold = $ceil(SIMILARITY_PERCENTAGE * maxLength);
        const editDistance = levenshtein(key, tagKey);
        if (editDistance <= threshold) {
            similarities.push([existingTags[key], tagName]);
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

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {Job} job
 * @param {Iterable<Tag>} [tags]
 */
export function applyTags(job, tags) {
    if (!tags?.length) {
        return;
    }
    const existingKeys = new Set(job.tags.map((t) => t.key));
    for (const tag of tags) {
        if (existingKeys.has(tag.key)) {
            continue;
        }
        const excluded = tag.exclude?.filter((key) => existingKeys.has(key));
        if (excluded?.length) {
            throw new HootError(
                `cannot apply tag ${stringify(tag.name)} on test/suite ${stringify(
                    job.name
                )} as it explicitly excludes tags ${excluded.map(stringify).join(" & ")}`
            );
        }
        job.tags.push(tag);
        existingKeys.add(tag.key);
        tag.weight++;
    }
}

/**
 * Globally defines specifications for a list of tags.
 * This is useful to add metadata or side-effects to a given tag, like an exclusion
 * to prevent specific tags to be added at the same time.
 *
 * @param {...TagDefinition} definitions
 * @example
 *  defineTags({
 *      name: "desktop",
 *      exclude: ["mobile"],
 *  });
 */
export function defineTags(...definitions) {
    return definitions.map((def) => {
        const tagKey = def.key || normalize(def.name);
        if (existingTags[tagKey]) {
            throw new HootError(`duplicate definition for tag "${def.name}"`);
        }
        checkTagSimilarity(tagKey, def.name);

        existingTags[tagKey] = new Tag(tagKey, def);

        return existingTags[tagKey];
    });
}

/**
 * @param {string[]} tagNames
 */
export function getTags(tagNames) {
    const tagKeys = tagNames.map(normalize);
    return tagKeys.map((tagKey, i) => {
        const tag = existingTags[tagKey] || defineTags({ key: tagKey, name: tagNames[i] })[0];
        return tag;
    });
}

export function getTagSimilarities() {
    return similarities;
}

/**
 * ! SHOULD NOT BE EXPORTED OUTSIDE OF HOOT
 *
 * Used in Hoot internal tests to remove tags introduced within a test.
 *
 * @private
 * @param  {Iterable<string>} tagKeys
 */
export function undefineTags(tagKeys) {
    for (const tagKey of tagKeys) {
        delete existingTags[tagKey];
    }
}

/**
 * Should **not** be instantiated outside of {@link defineTags}.
 * @see {@link defineTags}
 */
export class Tag {
    static DEBUG = "debug";
    static ONLY = "only";
    static SKIP = "skip";
    static TODO = "todo";

    weight = 0;

    get id() {
        return this.key;
    }

    /**
     * @param {string} key normalized tag name
     * @param {TagDefinition} definition
     */
    constructor(key, { name, exclude, before, after }) {
        this.key = key;
        this.name = name;
        this.color = TAG_COLORS[stringToNumber(this.key) % TAG_COLORS.length];
        if (exclude) {
            this.exclude = exclude.map(normalize);
        }
        if (before) {
            this.before = before;
        }
        if (after) {
            this.after = after;
        }
    }
}
