/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/_applyThreadDescription
        [Action/params]
            record
                [type]
                    ThreadViewTopbar
        [Action/behavior]
            :newDescription
                @record
                .{ThreadViewTopbar/pendingThreadDescription}
            {Record/update}
                [0]
                    @record
                [1]
                    [ThreadViewTopbar/isEditingThreadDescription]
                        false
                    [ThreadViewTopbar/pendingThreadDescription]
                        {Record/empty}
            {if}
                @newDescription
                .{!=}
                    @record
                    .{ThreadViewTopbar/thread}
                    .{Thread/description}
            .{then}
                {Thread/changeDescription}
                    [0]
                        @record
                        .{ThreadViewTopbar/thread}
                    [1]
                        @newDescription
`;
