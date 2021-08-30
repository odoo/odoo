/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            NotificationGroupComponent
        [Record/models]
            Hoverable
            NotificationListItemComponent/root
        [Element/onClick]
            {if}
                @record
                .{NotificationGroupComponent/markAsRead}
                .{&}
                    @record
                    .{NotificationGroupComponent/markAsRead}
                    .{web.Element/contains}
                        @ev
                        .{web.Event/target}
            .{then}
                {Dev/comment}
                    handled in _onClickMarkAsRead
                {break}
            {NotificationGroup/openDocuments}
                @record
                .{NotificationGroupComponent/notificationGroupView}
                .{NotificationGroupView/notificationGroup}
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
                        .o-NotificationGroupComponent-markAsRead
                    [1]
                        {Dev/comment}
                            TODO also mixin this
                            task-2258605
                        [web.scss/opacity]
                            1
`;
