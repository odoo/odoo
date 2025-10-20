import { compareDatetime } from "@mail/utils/common/misc";
import { fields, Record } from "@mail/core/common/record";
import { browser } from "@web/core/browser/browser";

export const DISCUSS_SIDEBAR_CATEGORY_FOLDED_LS = "discuss_sidebar_category_folded_";

export class DiscussAppCategory extends Record {
    static id = "id";

    static new() {
        const record = super.new(...arguments);
        record.onStorage = record.onStorage.bind(record);
        browser.addEventListener("storage", record.onStorage);
        return record;
    }

    delete() {
        browser.removeEventListener("storage", this.onStorage);
        super.delete(...arguments);
    }

    onStorage(ev) {
        if (ev.key === `${DISCUSS_SIDEBAR_CATEGORY_FOLDED_LS}${this.id}`) {
            this.is_open = ev.newValue !== "true";
        }
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
            return compareDatetime(t2.lastInterestDt, t1.lastInterestDt) || t2.id - t1.id;
        }
    }

    get isVisible() {
        return (
            !this.hideWhenEmpty ||
            this.threads.some((thread) => thread.displayToSelf || thread.isLocallyPinned)
        );
    }

    /** @type {string} */
    extraClass;
    /** @string */
    icon;
    /** @string */
    id;
    /** @type {string} */
    name;
    hideWhenEmpty = false;
    canView = false;
    app = fields.One("DiscussApp", {
        compute() {
            return this.store.discuss;
        },
    });
    /** @type {number} */
    sequence;

    is_open = fields.Attr(false, {
        /** @this {import("models").DiscussApp} */
        compute() {
            return !(
                browser.localStorage.getItem(`${DISCUSS_SIDEBAR_CATEGORY_FOLDED_LS}${this.id}`) ??
                false
            );
        },
        /** @this {import("models").DiscussApp} */
        onUpdate() {
            if (!this.is_open) {
                browser.localStorage.setItem(
                    `${DISCUSS_SIDEBAR_CATEGORY_FOLDED_LS}${this.id}`,
                    true
                );
            } else {
                browser.localStorage.removeItem(`${DISCUSS_SIDEBAR_CATEGORY_FOLDED_LS}${this.id}`);
            }
        },
    });

    threads = fields.Many("mail.thread", {
        sort(t1, t2) {
            return this.sortThreads(t1, t2);
        },
        inverse: "discussAppCategory",
    });
    threadsWithCounter = fields.Many("mail.thread", { inverse: "categoryAsThreadWithCounter" });
}

DiscussAppCategory.register();
