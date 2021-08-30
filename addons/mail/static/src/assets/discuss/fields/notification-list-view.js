/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            notificationListView
        [Field/model]
            Discuss
        [Field/type]
            one
        [Field/target]
            NotificationListView
        [Field/isCausal]
            true
        [Field/inverse]
            NotificationListView/discussOwner
        [Field/compute]
            {if}
                {Device/isMobile}
                .{&}
                    {Discuss/activeMobileNavbarTabId}
                    .{!=}
                        mailbox
            .{then}
                {Record/insert}
                    [Record/models]
                        NotificationListView
            .{else}
                {Record/empty}
`;
