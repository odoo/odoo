/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            notificationViews
        [Field/model]
            NotificationListView
        [Field/type]
            many
        [Field/target]
            NotificationView
        [Field/isCausal]
            true
        [Field/compute]
            :notifications
                {Record/insert}
                    [Record/models]
                        Collection
            {if}
                @record
                .{NotificationListView/notificationRequestView}
            .{then}
                {Collection/push}
                    [0]
                        @notifications
                    [1]
                        @record
                        .{NotificationListView/notificationRequestView}
            {Collection/push}
                [0]
                    @notifications
                []
                    @record
                    .{NotificationListView/notificationGroupViews}
                []
                    @record
                    .{NotificationListView/threadNeedactionPreviewViews}
                []
                    @record
                    .{NotificationListView/threadPreviewViews}
            @notifications
`;
