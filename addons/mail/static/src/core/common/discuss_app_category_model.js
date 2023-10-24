/* @odoo-module */

import { Record } from "./record";

export class DiscussAppCategory extends Record {
    static id = "id";
    /** @returns {import("models").DiscussAppCategory} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").DiscussAppCategory|import("models").DiscussAppCategory[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {string} */
    extraClass;
    /** @string */
    id;
    /** @type {string} */
    name;
    isOpen = false;
    canView = false;
    canAdd = false;
    /** @type {string} */
    serverStateKey;
    /** @type {string} */
    addTitle;
    /** @type {string} */
    addHotkey;
    threads = Record.many("Thread");
}

DiscussAppCategory.register();
