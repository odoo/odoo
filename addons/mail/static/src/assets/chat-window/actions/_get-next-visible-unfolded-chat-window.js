/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Cycles to the next possible visible and unfolded chat window starting
        from the 'currentChatWindow', following the natural order based on the
        current text direction, and with the possibility to 'reverse' based on
        the given parameter.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/_getNextVisibleUnfoldedChatWindow
        [Action/params]
            chatWindow
            reverse
                [default]
                    false
        [Action/behavior]
            :orderedVisible
                @chatWindow
                .{ChatWindow/manager}
                .{ChatWindowManager/allOrderedVisible}
            {Dev/comment}
                Return index of next visible chat window of a given visible chat
                window index. The direction of "next" chat window depends on
                reverse option.
            :_getNextIndex
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        index
                    [Function/out]
                        :directionOffset
                            {if}
                                @reverse
                            .{then}
                                1
                            .{else}
                                -1
                        :nextIndex
                            @index
                            .{+}
                                @directionOffset
                        {if}
                            @nextIndex
                            .{>}
                                @orderedVisible
                                .{Collection/length}
                                .{-}
                                    1
                        .{then}
                            :nextIndex
                                0
                        {if}
                            @nextIndex
                            .{<}
                                0
                        .{then}
                            :nextIndex
                                @orderedVisible
                                .{Collection/length}
                                .{-}
                                    1
                        @nextIndex
            :currentIndex
                @orderedVisible
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
            :nextIndex
                @_getNextIndex
                    @currentIndex
            :nextToFocus
                @orderedVisible
                .{Collection/at}
                    @nextIndex
            {while}
                nextToFocus
                .{ChatWindow/isFolded}
            .{do}
                :nextIndex
                    @_getNextIndex
                        @nextIndex
                :nextToFocus
                    @orderedVisible
                    .{Collection/at}
                        @nextIndex
            @nextToFocus
`;
