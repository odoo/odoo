import { NotificationItem } from "@mail/core/public_web/notification_item";

import { props, t } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";

/** @type {NotificationItem} */
const notificationItemPatch = {
    setup() {
        super.setup(...arguments);
        this.ratingProps = props({
            rating: t.instanceOf(this.store["rating.rating"].Class).optional(),
        });
    },
};
patch(NotificationItem.prototype, notificationItemPatch);
