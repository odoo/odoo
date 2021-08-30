/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Tab selected in this navbar.
        Either 'all', 'mailbox', 'chat' or 'channel'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activeTabId
        [Field/model]
            MobileMessagingNavbarView
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{MobileMessagingNavbarView/discuss}
            .{then}
                @record
                .{MobileMessagingNavbarView/discuss}
                .{Discuss/activeMobileNavbarTabId}
            .{elif}
                @record
                .{MobileMessagingNavbarView/messagingMenu}
            .{then}
                @record
                .{MobileMessagingNavbarView/messagingMenu}
                .{MessagingMenu/activeTabId}
            .{else}
                {Record/empty}
`;
