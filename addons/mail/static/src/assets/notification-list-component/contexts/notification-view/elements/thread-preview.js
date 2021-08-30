/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            threadPreview
        [Element/model]
            NotificationListComponent:notificationView
        [Field/target]
            ThreadPreviewComponent
        [Record/models]
            NotificationListComponent/preview
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
                    ThreadPreviewView
        [ThreadPreviewComponent/notificationView]
            @record
            .{NotificationListComponent:notificationView/notificationView}
`;
