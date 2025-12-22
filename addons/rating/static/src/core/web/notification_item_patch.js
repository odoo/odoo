/** @odoo-module */

import { NotificationItem } from "@mail/core/public_web/notification_item";

NotificationItem.props = [...NotificationItem.props, "rating?"];
