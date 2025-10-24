import { fields, Record } from "@mail/model/export";

export class DiscussApp extends Record {
    INSPECTOR_WIDTH = 300;
    COMPACT_SIDEBAR_WIDTH = 60;
    /** @type {'notification'|'channel'|'chat'|'livechat'|'inbox'} */
    activeTab = "notification";
    searchTerm = "";
    isActive = false;
    isMemberPanelOpenByDefault = fields.Attr(true, { localStorage: true });
    isSidebarCompact = fields.Attr(false, { localStorage: true });
    lastActiveId = fields.Attr(undefined, { localStorage: true });
    thread = fields.One("mail.thread", {
        /** @this {import("models").DiscussApp} */
        onUpdate() {
            this.lastActiveId = this.store["mail.thread"].localIdToActiveId(this.thread?.localId);
        },
    });
    hasRestoredThread = false;
}

DiscussApp.register();
