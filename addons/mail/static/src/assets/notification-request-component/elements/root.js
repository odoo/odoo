/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            NotificationRequestComponent
        [Record/models]
            Hoverable
            NotificationListItemComponent/root
        [Element/onClick]
            {if}
                {web.Browser/Notification}
            .{then}
                :permission
                    {web.WindowNotification/requestPermission}
                        {web.Browser/Notification}
                {if}
                    @permission
                .{then}
                    {NotificationRequestComponent/_handleResponseNotificationPermission}
                        @record
                        @permission
            {if}
                {Device/isMobile}
                .{isFalsy}
            .{then}
                {MessagingMenu/close}
        [web.Element/style]
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                {web.scss/selector}
                    [0]
                        .o-NotificationRequestComponent-partnerImStatusIcon
                    [1]
                        {scss/include}
                            {scss/o-mail-notification-list-item-hover-partner-im-status-icon-style}
`;
