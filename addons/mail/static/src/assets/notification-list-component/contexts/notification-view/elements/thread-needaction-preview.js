/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            threadNeedactionPreview
        [Element/model]
            NotificationListComponent:notificationView
        [Field/target]
            ThreadNeedactionPreviewComponent
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
                    ThreadNeedactionView
        [ThreadNeedactionPreviewComponent/view]
            @record
            .{NotificationListComponent:notificationView/notificationView}
`;
