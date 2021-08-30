/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Closes all chat windows related to the given thread.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindowManager/closeThread
        [Action/params]
            chatWindowManager
                [type]
                    ChatWindowManager
            options
                [type]
                    Object
            thread
                [type]
                    Thread
        [Action/behavior]
            {foreach}
                @chatWindowManager
                .{ChatWindowManager/chatWindows}
            .{as}
                chatWindow
            .{do}
                {if}
                    @chatWindow
                    .{ChatWindow/thread}
                    .{=}
                        @thread
                .{then}
                    {ChatWindow/close}
                        [0]
                            @chatWindow
                        [1]
                            @options
`;
