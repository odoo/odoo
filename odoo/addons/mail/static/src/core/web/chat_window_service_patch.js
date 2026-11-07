/* @odoo-module */

import { ChatWindowService } from "@mail/core/common/chat_window_service";

import { patch } from "@web/core/utils/patch";

patch(ChatWindowService.prototype, {
    async _onClose(chatWindow, options) {
        if (
            this.ui.isSmall &&
            !this.store.discuss.isActive &&
            chatWindow.openMessagingMenuOnClose
        ) {
            // If we are in mobile and discuss is not open, it means the
            // chat window was opened from the messaging menu. In that
            // case it should be re-opened to simulate it was always
            // there in the background.
            document.querySelector(".o_menu_systray i[aria-label='Messages']")?.click();
            // ensure messaging menu is opened before chat window is closed
            await Promise.resolve();
        }
        await super._onClose(chatWindow, options);
    },
});
