/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            separator
        [Element/model]
            NotificationListComponent:notificationView
        [Element/isPresent]
            @record
            .{NotificationListComponent/notificationListView}
            .{NotificationListView/notificationViews}
            .{Collection/length}
            .{!=}
                0
            .{&}
                @record
                .{NotificationListComponent/notificationListView}
                .{NotificationListView/notificationViews}
                .{Collection/last}
                .{!=}
                    @record
                    .{NotificationListComponent:notificationView/notificationView}
        [web.Element/style]
            [web.scss/flex]
                0
                0
                auto
            [web.scss/width]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/border-bottom]
                {scss/$border-width}
                solid
                {scss/$border-color}
`;
