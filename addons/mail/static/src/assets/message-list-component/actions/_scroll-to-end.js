/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Scrolls to the end of the list.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageListComponent/_scrollToEnd
        [Action/params]
            record
                [type]
                    MessageListComponent
        [Action/behavior]
            {MessageListComponent/setScrollTop}
                [0]
                    @record
                [1]
                    {if}
                        @record
                        .{MessageListComponent/order}
                        .{=}
                            asc
                    .{then}
                        {MessageListComponent/_getScrollableElement}
                            @record
                        .{web.Element/scrollHeight}
                        .{-}
                            {MessageListComponent/_getScrollableElement}
                                @record
                            .{web.Element/clientHeight}
                    .{else}
                        0
`;
