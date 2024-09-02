import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { patch } from "@web/core/utils/patch";

patch(MessagingMenu.prototype, {
    async onClickStartMeeting() {
        this.store.startMeeting();
        this.dropdown.close();
    },
});
