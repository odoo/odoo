import { compareDatetime } from "@mail/utils/common/misc";
import { fields, Record } from "@mail/model/export";

export class DiscussAppCategory extends Record {
    static id = "id";

    /**
     * @param {import("models").DiscussChannel} c1
     * @param {import("models").DiscussChannel} c2
     */
    sortChannels(c1, c2) {
        if (["channels", "favorites"].includes(this.id) || this.discussCategoryAsAppCategory) {
            return (
                (c1.displayName &&
                    String.prototype.localeCompare.call(c1.displayName, c2.displayName)) ||
                c2.id - c1.id
            );
        }
        return compareDatetime(c2.lastInterestDt, c1.lastInterestDt) || c2.id - c1.id;
    }

    get isVisible() {
        return (
            !this.hidden &&
            (!this.hideWhenEmpty ||
                this.channels.some(
                    (channel) => channel.self_member_id?.is_pinned || channel.isLocallyPinned
                ))
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
    // Hide categories from the devtools if really bothered.
    hidden = fields.Attr(undefined, {
        compute() {
            return Boolean(localStorage.getItem(`mail.sidebar_category_${this.id}_hidden`));
        },
        onUpdate() {
            if (!this.hidden && this.hidden !== undefined) {
                localStorage.removeItem(`mail.sidebar_category_${this.id}_hidden`);
            } else {
                localStorage.setItem(`mail.sidebar_category_${this.id}_hidden`, true);
            }
        },
        eager: true,
    });
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

    channels = fields.Many("discuss.channel", {
        sort(c1, c2) {
            return this.sortChannels(c1, c2);
        },
        inverse: "discussAppCategory",
    });
    channelsWithCounter = fields.Many("discuss.channel", {
        inverse: "categoryAsChannelWithCounter",
    });
}

DiscussAppCategory.register();
