/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewer/saveThreadCacheScrollHeightAsInitial
        [Action/params]
            threadViewer
                [type]
                    ThreadViewer
            scrollHeight
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
                    Initial scroll height is disabled for chatter because it is
                    too complex to handle correctly and less important
                    functionally.
                {break}
            {Record/update}
                [0]
                    @threadViewer
                [1]
                    [ThreadViewer/threadCacheInitialScrollHeights]
                        @threadViewer
                        .{ThreadViewer/threadCacheInitialScrollHeights}
                            {entry}
                                [key]
                                    @threadCache
                                    .{Record/id}
                                [value]
                                    @scrollHeight
`;
