import { NotificationItem } from "@mail/core/public_web/notification_item";
import { mergeProps } from "@mail/utils/common/hooks";

import { useProps, t } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";

/** @type {NotificationItem} */
const notificationItemPatch = {
    setup() {
        super.setup(...arguments);
        mergeProps(
            this.props,
            useProps({
                rating: t.instanceOf(this.store["rating.rating"]).optional(),
            })
        );
    },
};
patch(NotificationItem.prototype, notificationItemPatch);
