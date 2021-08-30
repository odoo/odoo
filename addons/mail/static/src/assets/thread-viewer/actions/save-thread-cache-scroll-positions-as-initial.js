/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewer/saveThreadCacheScrollPositionsAsInitial
        [Action/params]
            threadViewer
                [type]
                    ThreadViewer
            scrollTop
                [type]
                    Integer
            threadCache
                [type]
                    ThreadCache
        [Action/behavior]
            :threadCache
                @threadCache
                .{|}
                    @threadViewer
                    .{ThreadViewer/threadCache}
            {if}
                @threadCache
                .{isFalsy}
            .{then}
                {break}
            {if}
                @threadViewer
                .{ThreadViewer/chatter}
            .{then}
                {Dev/comment}
                    Initial scroll position is disabled for chatter because it is
                    too complex to handle correctly and less important
                    functionally.
                {break}
            {Record/update}
                [0]
                    @threadViewer
                [1]
                    [ThreadViewer/threadCacheInitialScrollPositions]
                        @threadViewer
                        .{ThreadViewer/threadCacheInitialScrollPositions}
                            {entry}
                                [key]
                                    @threadCache
                                    .{Record/id}
                                [value]
                                    @scrollTop
`;
