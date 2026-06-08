import { Message } from "@mail/core/common/message";

import { SnailmailNotificationPopover } from "./snailmail_notification_popover";

Message.components = {
    ...Message.components,
    Popover: SnailmailNotificationPopover,
};
