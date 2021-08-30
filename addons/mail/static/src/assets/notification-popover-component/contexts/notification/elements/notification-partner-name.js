/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            notificationPartnerName
        [Element/model]
            NotificationPopoverComponent:notification
        [web.Element/tag]
            span
        [Element/isPresent]
            @record
            .{NotificationPopoverComponent:notification/notification}
            .{Notification/partner}
        [web.Element/textContent]
            @record
            .{NotificationPopoverComponent:notification/notification}
            .{Notification/partner}
            .{Partner/nameOrDisplayName}
`;
