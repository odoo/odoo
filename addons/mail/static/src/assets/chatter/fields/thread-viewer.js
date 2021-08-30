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
            Chatter
        [Field/type]
            one
        [Field/target]
            ThreadViewer
        [Field/isCausal]
            true
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            ThreadViewer/chatter
        [Field/compute]
            {Record/insert}
                [Record/models]
                    ThreadViewer
                [ThreadViewer/hasThreadView]
                    @record
                    .{Chatter/hasThreadView}
                [ThreadViewer/order]
                    desc
                [ThreadViewer/thread]
                    {if}
                        @record
                        .{Chatter/thread}
                    .{then}
                        @record
                        .{Chatter/thread}
                    .{else}
                        {Record/empty}
`;
