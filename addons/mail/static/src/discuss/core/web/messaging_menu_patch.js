import { DiscussSearch } from "@mail/core/public_web/discuss_search";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
Object.assign(MessagingMenu.components, { DiscussSearch });

patch(MessagingMenu.prototype, {
    setup() {
        super.setup();
        this.command = useService("command");
    },
    beforeOpen() {
        const res = super.beforeOpen(...arguments);
        this.store.channels.fetch();
        return res;
    },
    onClickNewMessage() {
        this.command.openMainPalette({ searchValue: "@" });
        if (!this.ui.isSmall && !this.env.inDiscussApp) {
            this.dropdown.close();
        }
    },
});
