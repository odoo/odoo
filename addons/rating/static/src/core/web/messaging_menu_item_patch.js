import { MessagingMenuItem } from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import "@mail/discuss/core/public_web/messaging_menu_item_patch";

import { patch } from "@web/core/utils/patch";

/** @type {MessagingMenuItem} */
const messagingMenuItemPatch = {
    get notificationItemProps() {
        const itemProps = super.notificationItemProps;
        if (itemProps) {
            itemProps.rating = itemProps.message?.rating_id;
        }
        return itemProps;
    },
};
patch(MessagingMenuItem.prototype, messagingMenuItemPatch);
