/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            name
        [Element/model]
            NotificationGroupComponent
        [web.Element/tag]
            span
        [Record/models]
            NotificationListItemComponent/bold
            NotificationListItemComponent/name
        [web.Element/class]
            text-truncate
        [web.Element/textContent]
            @record
            .{NotificationGroupComponent/notificationGroupView}
            .{NotificationGroupView/notificationGroup}
            .{NotificationGroup/resModelName}
`;
