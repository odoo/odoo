/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            commandStar
        [Element/model]
            MessageViewComponent
        [Record/models]
            Hoverable
        [web.Element/style]
            [web.scss/font-size]
                1.3
                em
            {if}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/isStarred}
            .{then}
                [web.scss/color]
                    gold
                {if}
                    @field
                    .{web.Element/isHover}
                .{then}
                    [web.scss/filter]
                        {web.scss/brightness}
                            0.9
`;
