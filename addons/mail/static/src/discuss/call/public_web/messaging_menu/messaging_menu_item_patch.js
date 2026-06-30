import { MessagingMenuItem } from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import { MessagingMenuCallParticipants } from "@mail/discuss/call/public_web/messaging_menu/call_participants";

import { patch } from "@web/core/utils/patch";

MessagingMenuItem.components = { ...MessagingMenuItem.components, MessagingMenuCallParticipants };

patch(MessagingMenuItem.prototype, {
    get attClass() {
        return { ...super.attClass, "o-my-0_5": this.channel?.hasRtcSessionActive };
    },
});
