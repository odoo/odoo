/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            filter
        [Field/model]
            NotificationListView
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{NotificationListView/discussOwner}
            .{then}
                @record
                .{NotificationListView/discussOwner}
                .{Discuss/activeMobileNavbarTabId}
            .{elif}
                @record
                .{NotificationListView/messagingMenuOwner}
            .{then}
                @record
                .{NotificationListView/messagingMenuOwner}
                .{MessagingMenu/activeTabId}
            .{else}
                {Record/empty}
`;
