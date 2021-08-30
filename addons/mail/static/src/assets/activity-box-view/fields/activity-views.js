/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activityViews
        [Field/model]
            ActivityBoxView
        [Field/type]
            many
        [Field/target]
            ActivityView
        [Fild/isCausal]
            true
        [Field/inverse]
            ActivityView/activityBoxView
        [Field/compute]
            @record
            .{ActivityBoxView/chatter}
            .{Chatter/thread}
            .{Thread/activities}
            .{Collection/map}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        activity
                    [Function/out]
                        {Record/insert}
                            [Record/models]
                                ActivityView
                            [ActivityView/activity]
                                @activity
`;
