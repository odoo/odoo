import { patch } from "@web/core/utils/patch";
import { ChatWindowContainer } from "../common/chat_window_container";

patch(ChatWindowContainer.prototype, {
    get isShown() {
        return super.isShown && !this.store.discuss.isActive && !this.ui.isSmall;
    },
});
