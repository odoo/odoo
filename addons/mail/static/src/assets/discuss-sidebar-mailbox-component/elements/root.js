/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            DiscussSidebarMailboxComponent
        [Record/models]
            Hoverable
        [Element/onClick]
            {Thread/onClick}
                [0]
                    @record
                    .{DiscussSidebarMailboxComponent/mailbox}
                [1]
                    @ev
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/padding]
                [0]
                    {scss/map-get}
                        {scss/$spacers}
                        1
                [1]
                    0
            [web.scss/cursor]
                pointer
            {if}
                @record
                .{DiscussSidebarMailboxComponent/mailbox}
                .{=}
                    {Discuss/thread}
            .{then}
                [web.scss/background-color]
                    {scss/gray}
                        200
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/background-color]
                    {scss/gray}
                        300
`;
