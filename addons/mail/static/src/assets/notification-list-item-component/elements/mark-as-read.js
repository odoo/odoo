/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            markAsRead
        [Element/model]
            NotificationListItemComponent
        [Record/models]
            Hoverable
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex]
                0
                0
                auto
            [web.scss/opacity]
                0
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/color]
                    {scss/gray}
                        600
`;
