import { ChatWindow } from "@mail/core/common/chat_window_model";

import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    async _onClose(options) {
        if (
            this.store.env.services.ui.isSmall &&
            !this.store.discuss.isActive &&
            this.fromMessagingMenu
        ) {
            // If we are in mobile and discuss is not open, it means the
            // chat window was opened from the messaging menu. In that
            // case it should be re-opened to simulate it was always
            // there in the background.
            document.querySelector(".o_menu_systray i[aria-label='Messages']")?.click();
            // ensure messaging menu is opened before chat window is closed
            await Promise.resolve();
        }
        await super._onClose(...arguments);
    },
});
