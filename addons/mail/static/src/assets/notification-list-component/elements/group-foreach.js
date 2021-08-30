/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            groupForeach
        [Element/model]
            NotificationListComponent
        [Field/target]
            NotificationListComponent:notificationView
        [Record/models]
            Foreach
        [NotificationListComponent:notificationView/notificationView]
            @field
            .{Foreach/get}
                notificationView
        [Foreach/collection]
            @record
            .{NotificationListComponent/notificationListView}
            .{NotificationListView/notificationViews}
        [Foreach/as]
            notificationView
        [Element/key]
            @field
            .{Foreach/get}
                notificationView
            .{Record/id}
`;
