/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            notificationGroupViews
        [Field/model]
            NotificationListView
        [Field/type]
            many
        [Field/target]
            NotificationGroupView
        [Field/isCausal]
            true
        [Field/inverse]
            NotificationGroupView/notificationListViewOwner
        [Field/compute]
            {if}
                @record
                .{NotificationListView/filter}
                .{!=}
                    all
            .{then}
                {Record/empty}
            .{else}
                {Record/insert}
                    {Record/all}
                        [Record/models]
                            NotificationGroup
                    .{Collection/sort}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                group1
                                group2
                            [Function/out]
                                @group1
                                .{NotificationGroup/sequence}
                                .{-}
                                    @group2
                                    .{NotificationGroup/sequence}
                    .{Collection/map}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                notificationGroup
                            [Function/out]
                                [Record/models]
                                    NotificationGroupView
                                [NotificationGroupView/notificationGroup]
                                    @notificationGroup
`;
