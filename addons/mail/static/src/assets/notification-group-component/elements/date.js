/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            date
        [Element/model]
            NotificationGroupComponent
        [web.Element/tag]
            span
        [Record/models]
            NotificationListItemComponent/date
        [Element/isPresent]
            @record
            .{NotificationGroupComponent/notificationGroupView}
            .{NotificationGroupView/notificationGroup}
            .{NotificationGroup/date}
        [web.Element/textContent]
            @record
            .{NotificationGroupComponent/notificationGroupView}
            .{NotificationGroupView/notificationGroup}
            .{NotificationGroup/date}
            .{Moment/fromNow}
`;
