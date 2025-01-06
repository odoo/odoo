import { Record } from "@mail/core/common/record";
import { browser } from "@web/core/browser/browser";

export class DiscussApp extends Record {
    INSPECTOR_WIDTH = 300;
    /** @type {'main'|'channel'|'chat'|'livechat'} */
    activeTab = "main";
    searchTerm = "";
    isActive = false;
    isMemberPanelOpenByDefault = Record.attr(true, {
        compute() {
            return (
                browser.localStorage.getItem("mail.user_setting.no_members_default_open") !== "true"
            );
        },
        /** @this {import("models").DiscussApp} */
        onUpdate() {
            if (this.isMemberPanelOpenByDefault) {
                browser.localStorage.removeItem("mail.user_setting.no_members_default_open");
            } else {
                browser.localStorage.setItem("mail.user_setting.no_members_default_open", "true");
            }
        },
    });
    thread = Record.one("Thread");
    hasRestoredThread = false;
}

DiscussApp.register();
