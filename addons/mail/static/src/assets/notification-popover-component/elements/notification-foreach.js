/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            notificationForeach
        [Element/model]
            NotificationPopoverComponent
        [Field/target]
            NotificationPopoverComponent:notification
        [Record/models]
            Foreach
        [Foreach/collection]
            @record
            .{NotificationPopoverComponent/messageView}
            .{MessageView/message}
            .{Message/notifications}
        [Foreach/as]
            notification
        [Element/key]
            @field
            .{Foreach/get}
                notification
            .{Record/id}
        [NotificationPopoverComponent:notification/notification]
            @field
            .{Foreach/get}
                notification
`;
