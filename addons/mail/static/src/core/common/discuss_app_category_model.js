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
            return compareDatetime(t2.last_interest_dt, t1.last_interest_dt) || t2.id - t1.id;
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
    id;
    /** @type {string} */
    name;
    hideWhenEmpty = false;
    canView = false;
    canAdd = false;
    app = Record.one("DiscussApp", {
        compute() {
            return this._store.discuss;
        },
    });
    /** @type {number} */
    sequence;
    _openLocally = false;

    get open() {
        return this.serverStateKey ? this._store.settings[this.serverStateKey] : this._openLocally;
    }

    set open(value) {
        if (this.serverStateKey) {
            this._store.settings[this.serverStateKey] = value;
            this._store.env.services.orm.call(
                "res.users.settings",
                "set_res_users_settings",
                [[this._store.settings.id]],
                {
                    new_settings: {
                        [this.serverStateKey]: value,
                    },
                }
            );
        } else {
            this._openLocally = value;
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
