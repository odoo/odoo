/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            markAsRead
        [Element/model]
            NotificationGroupComponent
        [web.Element/tag]
            span
        [Record/models]
            NotificationGroupComponent/coreItem
            NotificationListItemComponent/markAsRead
        [web.Element/class]
            fa
            fa-check
        [web.Element/title]
            {Locale/text}
                Discard message delivery failures
        [Element/onClick]
            {NotificationGroup/openCancelAction}
                @record
                .{NotificationGroupComponent/notificationGroupView}
                .{NotificationGroupView/notificationGroup}
            {if}
                {Device/isMobile}
                .{isFalsy}
            .{then}
                {MessagingMenu/close}
`;
