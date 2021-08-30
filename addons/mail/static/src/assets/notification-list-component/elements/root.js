/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            NotificationListComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-flow]
                column
            [web.scss/overflow]
                auto
            {if}
                @record
                .{NotificationListComponent/notificationListView}
                .{NotificationListView/notificationViews}
                .{Collection/length}
                .{=}
                    0
            .{then}
                [web.scss/justify-content]
                    center
`;
