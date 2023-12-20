/* @odoo-module */

import { compareDatetime } from "@mail/utils/common/misc";
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

    /**
     * @param {import("models").Thread} t1
     * @param {import("models").Thread} t2
     */
    sortThreads(t1, t2) {
        if (this.id === "channels") {
            return String.prototype.localeCompare.call(t1.name, t2.name);
        }
        if (this.id === "chats") {
            return (
                compareDatetime(t2.lastInterestDateTime, t1.lastInterestDateTime) || t2.id - t1.id
            );
        }
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
    threads = Record.many("Thread", {
        sort(t1, t2) {
            return this.sortThreads(t1, t2);
        },
    });
}

DiscussAppCategory.register();
