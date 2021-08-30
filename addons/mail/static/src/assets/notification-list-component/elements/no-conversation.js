/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            noConversation
        [Element/model]
            NotificationListComponent
        [Element/isPresent]
            @record
            .{NotificationListComponent/notificationListView}
            .{NotificationListView/notificationViews}
            .{Collection/length}
            .{=}
                0
        [web.Element/textContent]
            {Locale/text}
                No conversation yet...
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/justify-content]
                center
            [web.scss/padding]
                [0]
                    {scss/map-get}
                        {scss/$spacers}
                        4
                [1]
                    {scss/map-get}
                        {scss/$spacers}
                        2
            [web.scss/color]
                {scss/$text-muted}
`;
