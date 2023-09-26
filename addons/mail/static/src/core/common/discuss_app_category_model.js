/* @odoo-module */

import { assignDefined } from "@mail/utils/common/misc";
import { Record } from "./record";

export class DiscussAppCategory extends Record {
    static id = "id";
    /** @returns {import("models").DiscussAppCategory} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").DiscussAppCategory} */
    static insert(data) {
        /** @type {import("models").DiscussAppCategory} */
        const category = this.preinsert(data);
        assignDefined(category, data);
        return category;
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
