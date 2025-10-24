import { compareDatetime } from "@mail/utils/common/misc";
import { fields, Record } from "@mail/model/export";

export class DiscussAppCategory extends Record {
    static id = "id";

    /**
     * @param {import("models").Thread} t1
     * @param {import("models").Thread} t2
     */
    sortThreads(t1, t2) {
        if (["channels", "favorites"].includes(this.id) || this.discussCategoryAsAppCategory) {
            return (
                (t1.displayName &&
                    String.prototype.localeCompare.call(t1.displayName, t2.displayName)) ||
                t2.id - t1.id
            );
        }
        return compareDatetime(t2.lastInterestDt, t1.lastInterestDt) || t2.id - t1.id;
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
    name = fields.Attr("", {
        compute() {
            return this.discussCategoryAsAppCategory?.name || this.name || "";
        },
    });
    discussCategoryAsAppCategory = fields.One("discuss.category", { inverse: "appCategory" });
    hideWhenEmpty = false;
    canView = false;
    app = fields.One("DiscussApp", {
        compute() {
            return this.store.discuss;
        },
    });
    /** @type {number} */
    sequence;

    is_open = fields.Attr(true, { localStorage: true });

    threads = fields.Many("mail.thread", {
        sort(t1, t2) {
            return this.sortThreads(t1, t2);
        },
        inverse: "discussAppCategory",
    });
    threadsWithCounter = fields.Many("mail.thread", { inverse: "categoryAsThreadWithCounter" });
}

DiscussAppCategory.register();
