import { fields, Record } from "@mail/model/export";

import { router } from "@web/core/browser/router";

export class DiscussApp extends Record {
    static singleton = true;

    INSPECTOR_WIDTH = 300;
    SIDEBAR_WIDTH = 400;
    messagingMenuSidebarState = fields.One("MessagingMenuState", {
        compute: () => ({ scope: "discuss.sidebar", activeTab: { id: "chat" } }),
    });
    isActive = false;
    isMemberPanelOpenByDefault = fields.Attr(true, { localStorage: true });
    lastActiveId = fields.Attr(undefined, { localStorage: true });
    thread = fields.One("mail.thread", {
        inverse: "discussAppAsThread",
        /** @this {import("models").DiscussApp} */
        onUpdate() {
            this.lastActiveId = this.store["mail.thread"].localIdToActiveId(this.thread?.localId);
            if (this.thread) {
                const menu = this.store.messagingMenu;
                if (this.messagingMenuSidebarState.activeTab?.notEq(menu.bookmarkTab)) {
                    this.messagingMenuSidebarState.activeTab =
                        this.thread.channel?.primaryMessagingMenuTab ?? menu.visibleTabs[0];
                }
            }
        },
    });
    hasRestoredThread = false;
    sidebarWidth = fields.Attr(undefined, { localStorage: true });

    /**
     * Write the current discuss selection to the URL and action context so it survives
     * browser history navigation. `activeId` is a thread token (e.g. `discuss.channel_10`)
     * when a conversation is open, or a tab token (e.g. `discuss.tab_notification`) when only a tab
     * is selected.
     *
     * @param {string} activeId
     */
    setActiveURL(activeId) {
        router.pushState({ active_id: activeId });
        const action = this.store.env.services.action;
        if (
            this.store.action_discuss_id &&
            action?.currentController?.action.id === this.store.action_discuss_id
        ) {
            // Keep the action stack up to date (used by breadcrumbs).
            action.currentController.action.context.active_id = activeId;
        }
    }

    /** @param {import("@mail/core/common/action").Action} [nextActiveAction] */
    shouldDisableMemberPanelAutoOpenFromClose(nextActiveAction) {
        return true;
    }
}

DiscussApp.register();
