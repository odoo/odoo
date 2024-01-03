/** @odoo-module */

import { isIterable } from "@web/../lib/hoot-dom/hoot_dom_utils";
import { HootError, normalize, stringToNumber } from "../hoot_utils";

/**
 * @typedef {import("./suite").Suite} Suite
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const SPECIAL_TAGS = {
    debug: "debug",
    only: "only",
    skip: "skip",
    todo: "todo",
};

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
 *
 * @param {string | Tag} tagName
 * @returns {Tag}
 */
export function createTag(tagName) {
    if (tagName instanceof Tag) {
        return tagName;
    } else {
        if (!existingTags[tagName]) {
            canCreateTag = true;
            existingTags[tagName] = new Tag(tagName);
            canCreateTag = false;
        }
        return existingTags[tagName];
    }
}

/**
 * @param  {...(string | Tag)[]} tagLists
 * @returns {Tag[]}
 */
export function createTags(...tagLists) {
    /** @type {Tag[]} */
    const tags = [];
    for (const tagList of tagLists) {
        if (!isIterable(tagList)) {
            continue;
        }
        for (const tagName of tagList) {
            const tag = createTag(tagName);
            if (tag && !tags.includes(tag)) {
                tags.push(tag);
            }
        }
    }
    return tags;
}

/**
 * Cannot be instantiated outside of {@link createTag}.
 * @see {@link createTag}
 */
export class Tag {
    static DEBUG = SPECIAL_TAGS.debug;
    static ONLY = SPECIAL_TAGS.only;
    static SKIP = SPECIAL_TAGS.skip;
    static TODO = SPECIAL_TAGS.todo;

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

        this.special = this.name in SPECIAL_TAGS;
        this.color = TAG_COLORS[stringToNumber(this.id) % TAG_COLORS.length];
    }
}
