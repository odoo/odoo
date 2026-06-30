import { MessagingMenuUIState } from "@mail/core/public_web/messaging_menu/messaging_menu_ui_state_model";

import { patch } from "@web/core/utils/patch";

patch(MessagingMenuUIState.prototype, {
    selectTab(tab) {
        super.selectTab(tab);
        if (this.id === "discuss.sidebar") {
            this.store.discuss.thread = null;
            this.store.discuss.setActiveURL(`discuss.tab_${tab.id}`);
        }
    },
    _isReadyForInitialLoad() {
        if (this.id === "discuss.sidebar") {
            // Defer until the thread has been restored from the URL/action, so a channel
            // in the URL doesn't load the default tab (chat) before settling on another
            // one.
            return this.store.discuss.hasRestoredThread;
        }
        return super._isReadyForInitialLoad();
    },
});
