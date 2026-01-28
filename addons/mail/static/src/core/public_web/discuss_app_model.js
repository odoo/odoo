import { fields, Record } from "@mail/core/common/record";
import { browser } from "@web/core/browser/browser";

export const NO_MEMBERS_DEFAULT_OPEN_LS = "mail.user_setting.no_members_default_open";
export const DISCUSS_SIDEBAR_COMPACT_LS = "mail.user_setting.discuss_sidebar_compact";
export class DiscussApp extends Record {
    INSPECTOR_WIDTH = 300;
    /** @type {'main'|'channel'|'chat'|'livechat'} */
    activeTab = "main";
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
    thread = fields.One("Thread");
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
}

DiscussApp.register();
