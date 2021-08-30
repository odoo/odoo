/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            mark done popover close on ESCAPE
        [Test/model]
            ActivityComponent
        [Test/assertions]
            2
        [Test/scenario]
            {Dev/comment}
                This test is not in activity_mark_done_popover_tests.js as it
                requires the activity mark done component to have a parent in
                order to allow testing interactions the popover.
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            @testEnv
            .{Record/insert}
                []
                    [Record/models]
                        res.partner
                    [res.partner/activity_ids]
                        12
                    [res.partner/id]
                        100
                []
                    [Record/models]
                        mail.activity
                    [mail.activity/activity_category]
                        default
                    [mail.activity/activity_type_id]
                        1
                    [mail.activity/can_write]
                        true
                    [mail.activity/id]
                        12
                    [mail.activity/res_id]
                        100
                    [mail.activity/res_model]
                        res.partner
            @testEnv
            .{Record/insert}
                [Record/models]
                    ChatterContainerComponent
                [ChatterContainerComponent/threadId]
                    100
                [ChatterContainerComponent/threadModel]
                    res.partner
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/markDoneButton}
            {Test/assert}
                []
                    @activity
                    .{Activity/activityMarkDonePopoverComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    Popover component should be present

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/keydown}
                    [0]
                        @activity
                        .{Activity/activityMarkDonePopoverComponents}
                        .{Collection/first}
                    [1]
                        [bubbles]
                            true
                        [key]
                            Escape
            {Test/assert}
                @activity
                .{Activity/activityMarkDonePopoverComponents}
                .{Collection/length}
                .{=}
                    0
`;
