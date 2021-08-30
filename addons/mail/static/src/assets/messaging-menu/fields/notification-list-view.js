/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The navbar view on the messaging menu when in mobile.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            notificationListView
        [Field/model]
            MessagingMenu
        [Field/type]
            one
        [Field/target]
            NotificationListView
        [Field/isCausal]
            true
        [Field/inverse]
            NotificationListView/messagingMenu
        [Field/compute]
            {if}
                @record
                .{MessagingMenu/isOpen}
            .{then}
                {Record/insert}
                    [Record/models]
                        NotificationListView
            .{else}
                {Record/empty}
`;
