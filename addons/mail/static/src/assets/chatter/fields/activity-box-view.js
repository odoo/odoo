/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activityBoxView
        [Field/model]
            Chatter
        [Field/type]
            one
        [Field/target]
            ActivityBoxView
        [Field/isCausal]
            true
        [Field/inverse]
            ActivityBoxView/chatter
        [Field/compute]
            {if}
                @record
                .{Chatter/thread}
                .{&}
                    @record
                    .{Chatter/thread}
                    .{Thread/hasActivities}
                .{&}
                    @record
                    .{Chatter/thread}
                    .{Thread/activities}
                    .{Collection/length}
                    .{>}
                        0
            .{then}
                {Record/insert}
                    [Record/models]
                        ActivityBoxView
            .{else}
                {Record/empty}
`;
