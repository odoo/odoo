/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the 'Activity' that belongs to 'this' and that are
        overdue (due earlier than today).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            overdueActivities
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Activity
        [Field/compute]
            @record
            .{Thread/activities}
            .{Collection/filter}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        item
                    [Function/out]
                        @item
                        .{Activity/state}
                        .{=}
                            overdue
`;
