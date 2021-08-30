/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            notificationRequest
        [Element/model]
            NotificationListComponent:notificationView
        [Field/target]
            NotificationRequestComponent
        [Element/isPresent]
            @record
            .{NotificationListComponent:notificationView/notificationView}
            .{NotificationView/type}
            .{=}
                NotificationRequestView
        [NotificationRequestComponent/view]
            @record
            .{NotificationListComponent:notificationView/notificationView}
`;
