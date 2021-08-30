/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ThreadViewer
        [Model/fields]
            chatter
            chatWindow
            compact
            discuss
            discussPublicView
            extraClass
            hasMemberList
            hasThreadView
            hasTopbar
            order
            thread
            threadCache
            threadCacheInitialScrollHeights
            threadCacheInitialScrollPositions
            threadView
        [Model/id]
            ThreadViewer/chatter
            .{|}
                ThreadViewer/chatWindow
            .{|}
                ThreadViewer/discuss
            .{|}
                ThreadViewer/discussPublicView
        [Model/actions]
            ThreadViewer/saveThreadCacheScrollHeightAsInitial
            ThreadViewer/saveThreadCacheScrollPositionsAsInitial
`;
