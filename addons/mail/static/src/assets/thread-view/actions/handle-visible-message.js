/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadView/handleVisibleMessage
        [Action/params]
            threadView
                [type]
                    ThreadView
            message
                [type]
                    Message
        [Action/behavior]
            {if}
                @threadView
                .{ThreadView/lastVisibleMessage}
                .{isFalsy}
                .{|}
                    @threadView
                    .{ThreadView/lastVisibleMessage}
                    .{Message/id}
                    .{<}
                        @message
                        .{Message/id}
            .{then}
                {Record/update}
                    [0]
                        @threadView
                    [1]
                        [ThreadView/lastVisibleMessage]
                            @message
`;
