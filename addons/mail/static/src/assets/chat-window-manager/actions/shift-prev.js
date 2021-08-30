/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Shift provided chat window to previous visible index, which swap
        visible order of this chat window and the preceding visible one
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindowManager/shiftPrev
        [Action/params]
            chatWindow
            chatWindowManager
        [Action/behavior]
            :index
                @chatWindowManager
                .{ChatWindowManager/allOrdered}
                .{Collection/findIndex}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            item
                        [Function/out]
                            @item
                            .{=}
                                @chatWindow
            {if}
                @index
                .{=}
                    @chatWindowManager
                    .{ChatWindowManager/allOrdered}
                    .{Collection/length}
                    .{-}
                        1
            .{then}
                {Dev/comment}
                    already first one
                {break}
            :otherChatWindow
                @chatWindowManager
                .{ChatWindowManager/allOrdered}
                .{Collection/at}
                    @index
                    .{+}
                        1
            :_newOrdered
                @chatWindowManager
                .{ChatWindowManager/allOrdered}
            {Record/update}
                [0]
                    @_newOrdered
                [1]
                    {entry}
                        [key]
                            Collection/
                            .{+}
                                @index
                        [value]
                            @otherChatWindow
                    {entry}
                        [key]
                            Collection/
                            .{+}
                                @index
                                .{+}
                                    1
                        [value]
                            @chatWindow
            {Record/update}
                [0]
                    @chatWindowManager
                [1]
                    [ChatWindowManager/allOrdered]
                        @_newOrdered
            {ChatWindow/focus}
                @chatWindow
`;
