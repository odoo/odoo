import { NotificationItem } from "@mail/core/public_web/notification_item";

import { patch } from "@web/core/utils/patch";

/** @type {NotificationItem} */
const notificationItemComponentPatch = {
    get attClass() {
        return {
            ...super.attClass,
            "o-selfMember": this.props.thread?.channel?.self_member_id,
            "o-help": this.props.thread?.channel?.livechat_status === "need_help",
        };
    },
};
patch(NotificationItem.prototype, notificationItemComponentPatch);
