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
            Discuss
        [Field/type]
            one
        [Field/target]
            ThreadViewer
        [Field/isCausal]
            true
        [Field/readonly]
            true
        [Field/required]
            true
        [Field/inverse]
            ThreadViewer/discuss
        [Field/compute]
            {Record/insert}
                [Record/models]
                    ThreadViewer
                [ThreadViewer/hasMemberList]
                    true
                [ThreadViewer/hasThreadView]
                    @record
                    .{Discuss/hasThreadView}
                [ThreadViewer/hasTopbar]
                    true
                [ThreadViewer/thread]
                    {if}
                        @record
                        .{Discuss/thread}
                    .{then}
                        @record
                        .{Discuss/thread}
                    .{else}
                        {Record/empty}
`;
