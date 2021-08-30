/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Make this message viewable in its enclosing scroll environment (usually
        message list).
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageViewComponent/scrollIntoView
        [Action/params]
            behavior
                [type]
                    String
                [default]
                    auto
            block
                [type]
                    String
                [default]
                    end
            record
                [type]
                    MessageViewComponent
        [Action/behavior]
            {UI/scrollIntoView}
                [0]
                    @record
                    .{MessageViewComponent/root}
                [1]
                    [behavior]
                        @behavior
                    [block]
                        @block
                    [inline]
                        nearest
            {if}
                @behavior
                .{=}
                    smooth
            .{then}
                {Record/insert}
                    [Record/models]
                        Promise
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            resolve
                        [Function/out]
                            {Record/insert}
                                [Record/models]
                                    Timer
                                [Timer/timeout]
                                    @resolve
                                [Timer/duration]
                                    500
                            .{Timer/start}
`;
