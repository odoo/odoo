import { MessagingMenuState } from "@mail/core/public_web/messaging_menu/messaging_menu_state_model";

import { patch } from "@web/core/utils/patch";

patch(MessagingMenuState.prototype, {
    selectTab(tab) {
        super.selectTab(tab);
        if (this.scope === "discuss.sidebar") {
            this.store.discuss.thread = null;
            this.store.discuss.setActiveURL(`discuss.tab_${tab.id}`);
        }
    },
});
