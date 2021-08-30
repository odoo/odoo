/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inlineText
        [Element/model]
            NotificationGroupComponent
        [web.Element/tag]
            span
        [Record/models]
            NotificationGroupComponent/coreItem
            NotificationListItemComponent/inlineText
        [web.Element/class]
            text-truncate
        [web.Element/textContent]
            {if}
                @record
                .{NotificationGroupComponent/notificationGroupView}
                .{NotificationGroupView/notificationGroup}
                .{NotificationGroup/type}
                .{=}
                    email
            .{then}
                {Locale/text}
                    An error occurred when sending an email.
`;
