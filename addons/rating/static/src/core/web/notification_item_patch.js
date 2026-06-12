import { notificationItemProps } from "@mail/core/public_web/notification_item";
import { t } from "@odoo/owl";

Object.assign(notificationItemProps, { rating: t.any().optional() });
