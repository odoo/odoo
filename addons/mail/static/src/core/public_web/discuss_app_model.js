import { fields, Record } from "@mail/core/common/record";
import { browser } from "@web/core/browser/browser";

export const NO_MEMBERS_DEFAULT_OPEN_LS = "mail.user_setting.no_members_default_open";
export const DISCUSS_SIDEBAR_COMPACT_LS = "mail.user_setting.discuss_sidebar_compact";
export const LAST_DISCUSS_ACTIVE_ID_LS = "mail.user_setting.discuss_last_active_id";

export class DiscussApp extends Record {
    INSPECTOR_WIDTH = 300;
    COMPACT_SIDEBAR_WIDTH = 60;
    /** @type {'notification'|'channel'|'chat'|'livechat'|'inbox'} */
    activeTab = "notification";
    searchTerm = "";
    isActive = false;
    _recomputeIsMemberPanelOpenByDefault = 0;
    isMemberPanelOpenByDefault = fields.Attr(true, {
        compute() {
            void this._recomputeIsMemberPanelOpenByDefault;
            return browser.localStorage.getItem(NO_MEMBERS_DEFAULT_OPEN_LS) !== "true";
        },
    });
    _recomputeIsSidebarCompact = 0;
    isSidebarCompact = fields.Attr(false, {
        compute() {
            void this._recomputeIsSidebarCompact;
            return browser.localStorage.getItem(DISCUSS_SIDEBAR_COMPACT_LS) === "true";
        },
    });
    lastActiveId = fields.Attr(undefined, {
        /** @this {import("models").DiscussApp} */
        compute() {
            return browser.localStorage.getItem(LAST_DISCUSS_ACTIVE_ID_LS) ?? undefined;
        },
        /** @this {import("models").DiscussApp} */
        onUpdate() {
            if (this.lastActiveId) {
                browser.localStorage.setItem(LAST_DISCUSS_ACTIVE_ID_LS, this.lastActiveId);
            } else {
                browser.localStorage.removeItem(LAST_DISCUSS_ACTIVE_ID_LS);
            }
        },
    });
    thread = fields.One("Thread", {
        /** @this {import("models").DiscussApp} */
        onUpdate() {
            this._threadOnUpdate();
        },
    });
    hasRestoredThread = false;

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
        if (ev.key === DISCUSS_SIDEBAR_COMPACT_LS) {
            this._recomputeIsSidebarCompact++;
        }
        if (ev.key === NO_MEMBERS_DEFAULT_OPEN_LS) {
            this._recomputeIsMemberPanelOpenByDefault++;
        }
    }

    /** @param {import("@mail/core/common/action").Action} [nextActiveAction] */
    shouldDisableMemberPanelAutoOpenFromClose(nextActiveAction) {
        return true;
    }

    _threadOnUpdate() {
        this.lastActiveId = this.store.Thread.localIdToActiveId(this.thread?.localId);
    }
}

DiscussApp.register();
