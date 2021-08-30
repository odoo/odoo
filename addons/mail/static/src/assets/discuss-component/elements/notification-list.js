/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            notificationList
        [Element/model]
            DiscussComponent
        [Field/target]
            NotificationListComponent
        [Element/isPresent]
            {Device/isMobile}
            .{&}
                {Discuss/activeMobileNavbarTabId}
                .{!=}
                    mailbox
            .{&}
                {Discuss/notificationListView}
        [NotificationListComponent/notificationListView]
            @record
            .{DiscussComponent/discussView}
            .{DiscussView/discuss}
            .{Discuss/notificationListView}
        [web.Element/style]
            [web.scss/width]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/flex]
                1
                1
                0
`;
