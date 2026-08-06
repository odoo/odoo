import { NotificationItem } from "@mail/core/public_web/notification_item";

import { useProps, t } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";

/** @type {NotificationItem} */
const notificationItemPatch = {
    setup() {
        super.setup(...arguments);
        this.ratingProps = useProps({
            rating: t.instanceOf(this.store["rating.rating"]).optional(),
        });
    },
};
patch(NotificationItem.prototype, notificationItemPatch);
