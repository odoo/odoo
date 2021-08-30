/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            simplest layout with force next
        [Test/model]
            ActivityMarkDonePopoverComponent
        [Test/assertions]
            6
        [Test/scenario]
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
                        not_upload_file
                    [mail.activity/can_write]
                        true
                    [mail.activity/chaining_type]
                        trigger
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
            {Test/assert}
                []
                    @activity
                    .{Activity/activityMarkDonePopoverComponents}
                    .{Collection/first}
                    .{ActivityMarkDonePopoverComponent/feedback}
                []
                    Popover component should contain the feedback textarea
            {Test/assert}
                []
                    @activity
                    .{Activity/activityMarkDonePopoverComponents}
                    .{Collection/first}
                    .{ActivityMarkDonePopoverComponent/buttons}
                []
                    Popover component should contain the action buttons
            {Test/assert}
                []
                    @activity
                    .{Activity/activityMarkDonePopoverComponents}
                    .{Collection/first}
                    .{ActivityMarkDonePopoverComponent/doneScheduleNextButton}
                []
                    Popover component should contain the done & schedule next button
            {Test/assert}
                []
                    @activity
                    .{Activity/activityMarkDonePopoverComponents}
                    .{Collection/first}
                    .{ActivityMarkDonePopoverComponent/doneButton}
                    .{isFalsy}
                []
                    Popover component should NOT contain the done button
            {Test/assert}
                []
                    @activity
                    .{Activity/activityMarkDonePopoverComponents}
                    .{Collection/first}
                    .{ActivityMarkDonePopoverComponent/discardButton}
                []
                    Popover component should contain the discard button
`;
