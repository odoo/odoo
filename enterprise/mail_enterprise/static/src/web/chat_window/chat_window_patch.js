import { ChatWindow } from "@mail/core/common/chat_window";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

import { useBackButton } from "@web_mobile/js/core/hooks";

patch(ChatWindow.prototype, {
    setup() {
        super.setup();
        useBackButton(() => this.props.chatWindow.close());
        this.homeMenuService = useService("home_menu");
    },
});
