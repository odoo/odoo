import { MENU_TABS } from "@mail/core/public_web/messaging_menu/messaging_menu_model";
import { Record, fields } from "@mail/model/export";

import { router } from "@web/core/browser/router";

const SIDEBAR_WIDTH = 400;

export class DiscussApp extends Record {
    static singleton = true;

    setup() {
        super.setup();
        this.onChange(
            () => [this.thread, this.thread?.channel?.primaryMessagingMenuTab],
            function onChangeThread(thread, primaryMessagingMenuTab) {
                this.lastActiveId = this.store["mail.thread"].localIdToActiveId(thread?.localId);
                if (thread) {
                    const menu = this.store.messagingMenu;
                    if (this.sidebarState?.activeTab?.notEq(menu.bookmarkTab)) {
                        const fallback = this.store.inPublicPage ? menu.channelTab : menu.chatTab;
                        this.sidebarState.activeTab = primaryMessagingMenuTab ?? fallback;
                    }
                }
            },
            { immediate: true, initialRun: false }
        );
    }

    INSPECTOR_WIDTH = 300;
    sidebarState = this.computed(
        () =>
            this.store.MessagingMenuUIState.get("discuss.sidebar") ??
            this.store.MessagingMenuUIState.insert({
                id: "discuss.sidebar",
                activeTab: this.store.inPublicPage ? MENU_TABS.CHANNEL : MENU_TABS.CHAT,
            })
    );
    isActive = false;
    isMemberPanelOpenByDefault = this.localStorage(true);
    lastActiveId = this.localStorage(undefined);
    thread = fields.One("mail.thread", {
        inverse: "discussAppAsThread",
    });
    hasRestoredThread = false;
    sidebarWidth = this.localStorage(SIDEBAR_WIDTH);

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
            // Sync the action service's own state, or a later `action.restore()` (e.g.
            // a `soft_reload`) rebuilds the URL from a stale, frozen `active_id` instead.
            action?.currentController.props.updateActionState?.(action?.currentController, {
                active_id: activeId,
            });
        }
    }

    /** @param {import("@mail/core/common/action").Action} [nextActiveAction] */
    shouldDisableMemberPanelAutoOpenFromClose(nextActiveAction) {
        return true;
    }
}

DiscussApp.register();
