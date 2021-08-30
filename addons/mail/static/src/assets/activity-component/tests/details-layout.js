/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            details layout
        [Test/model]
            ActivityComponent
        [Test/assertions]
            11
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
            :today
                {Record/insert}
                    [Record/models]
                        Date
            :tomorrow
                {Record/insert}
                    [Record/models]
                        Date
                .{Date/setDate}
                    @today
                    .{Date/getDate}
                    .{+}
                        1
            @testEnv
            .{Record/insert}
                []
                    [Record/models]
                        res.users
                    [res.users/id]
                        10
                    [res.users/name]
                        Pauvre pomme
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
                    [mail.activity/activity_type_id]
                        1
                    [mail.activity/create_date]
                        {Date/toString}
                            @today
                    [mail.activity/create_uid]
                        2
                    [mail.activity/date_deadline]
                        {Date/toString}
                            @tomorrow
                    [mail.activity/id]
                        12
                    [mail.activity/res_id]
                        100
                    [mail.activity/res_model]
                        res.partner
                    [mail.activity/state]
                        planned
                    [mail.activity/user_id]
                        10
            @testEnv
            .{Record/insert}
                [Record/models]
                    ChatterContainerComponent
                [ChatterContainerComponent/threadId]
                    100
                [ChatterContainerComponent/threadModel]
                    res.partner
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have activity component
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/userAvatar}
                []
                    should have activity user avatar
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/detailsButton}
                []
                    activity should have a details button

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/detailsButton}
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/details}
                []
                    activity details should be visible after clicking on details button
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/descriptionDetailType}
                []
                    activity details should have type
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/descriptionDetailType}
                    .{web.Element/textContent}
                    .{=}
                        Email
                []
                    activity details type should be 'Email'
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/detailsCreation}
                []
                    activity details should have creation date
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/detailsCreator}
                []
                    activity details should have creator
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/detailsAssignation}
                []
                    activity details should have assignation information
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/detailsAssignation}
                    .{web.Element/textContent}
                    .{String/startsWith}
                        Pauvre pomme
                []
                    activity details assignation information should contain creator display name
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/detailsAssignationUserAvatar}
                []
                    activity details should have user avatar
`;
