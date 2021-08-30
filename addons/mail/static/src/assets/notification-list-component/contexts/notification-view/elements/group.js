/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            group
        [Element/model]
            NotificationListComponent:notificationView
        [Field/target]
            NotificationGroupComponent
        [Element/isPresent]
            @record
            .{NotificationListComponent/notificationListView}
            .{NotificationListView/notificationViews}
            .{Collection/length}
            .{!=}
                0
            .{&}
                @record
                .{NotificationListComponent:notificationView/notificationView}
                .{NotificationView/type}
                .{=}
                    NotificationGroupView
        [NotificationGroupComponent/notificationGroupView]
            @record
            .{NotificationListComponent:notificationView/notificationView}
`;
