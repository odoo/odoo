/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            notificationIcon
        [Element/model]
            NotificationPopoverComponent:notification
        [web.Element/tag]
            i
        [web.Element/class]
            @record
            .{NotificationPopoverComponent:notification/notification}
            .{Notification/iconClass}
        [web.Element/title]
            @record
            .{NotificationPopoverComponent:notification/notification}
            .{Notification/iconTitle}
        [web.Element/role]
            img
        [web.Element/style]
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    2
`;
