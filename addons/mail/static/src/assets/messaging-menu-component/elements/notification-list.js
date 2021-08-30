/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            notificationList
        [Element/model]
            MessagingMenuComponent
        [Field/target]
            NotificationListComponent
        [Element/isPresent]
            {Messaging/isInitialized}
            .{&}
                {MessagingMenu/notificationListView}
        [NotificationListComponent/notificationListView]
            {MessagingMenu/notificationListView}
        [web.Element/style]
            {if}
                {Device/isMobile}
            .{then}
                [web.scss/flex]
                    1
                    1
                    auto
                [web.scss/overflow-y]
                    auto
`;
