import { compareDatetime } from "@mail/utils/common/misc";
import { Record } from "@mail/core/common/record";
import { browser } from "@web/core/browser/browser";

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
    canAdd = false;
    app = Record.one("DiscussApp", {
        compute() {
            return this.store.discuss;
        },
    });
    _openLocally = false;
    localStateKey = Record.attr(null, {
        compute() {
            if (this.saveStateToServer) {
                return null;
            }
            return `discuss_sidebar_category_${this.id}_open`;
        },
        onUpdate() {
            if (this.localStateKey) {
                this._openLocally = JSON.parse(
                    browser.localStorage.getItem(this.localStateKey) ?? "true"
                );
            }
        },
    });
    /** @type {number} */
    sequence;

    get open() {
        return this.saveStateToServer
            ? this.store.settings[this.serverStateKey]
            : this._openLocally;
    }

    get saveStateToServer() {
        return this.serverStateKey && this.store.self?.isInternalUser;
    }

    set open(value) {
        if (this.saveStateToServer) {
            this.store.settings[this.serverStateKey] = value;
            this.store.env.services.orm.call(
                "res.users.settings",
                "set_res_users_settings",
                [[this.store.settings.id]],
                {
                    new_settings: {
                        [this.serverStateKey]: value,
                    },
                }
            );
        } else {
            this._openLocally = value;
            browser.localStorage.setItem(this.localStateKey, value);
        }
    }

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
        inverse: "discussAppCategory",
    });
}

DiscussAppCategory.register();
