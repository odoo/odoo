/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            chatWindowHeader
        [Element/model]
            ChatWindowHiddenMenuComponent:listItem
        [Field/target]
            ChatWindowHeaderComponent
        [Record/models]
            Hoverable
        [ChatWindowHeaderComponent/chatWindow]
            @record
            .{ChatWindowHiddenMenuComponent:listItem/chatWindow}
        [web.Element/style]
            [web.scss/max-width]
                200
                px
            [web.scss/opacity]
                0.95
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/opacity]
                    1
`;
