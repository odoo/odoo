/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the 'ThreadViewer' managing the display of 'this.thread'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadViewer
        [Field/model]
            ChatWindow
        [Field/type]
            one
        [Field/target]
            ThreadViewer
        [Field/isCausal]
            true
        [Field/required]
            true
        [Field/inverse]
            ThreadViewer/chatWindow
        [Field/compute]
            {Record/insert}
                [Record/models]
                    ThreadViewer
                [ThreadViewer/compact]
                    true
                [ThreadViewer/hasThreadView]
                    @record
                    .{ChatWindow/hasThreadView}
                [ThreadViewer/thread]
                    {if}
                        @record
                        .{ChatWindow/thread}
                    .{then}
                        @record
                        .{ChatWindow/thread}
                    .{else}
                        {Record/empty}
`;
