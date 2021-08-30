/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            button related to file uploading is replaced when updating activity type from "Upload Document" to "Email"
        [Test/model]
            ActivityComponent
        [Test/assertions]
            2
        [Test/scenario]
            :activityId
                513
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                []
                    [Record/models]
                        res.partner
                    [res.partner/activity_ids]
                        @activityId
                    [res.partner/id]
                        100
                []
                    [Record/models]
                        mail.activity
                    [mail.activity/activity_category]
                        upload_file
                    [mail.activity/activity_type_id]
                        28
                    [mail.activity/can_write]
                        true
                    [mail.activity/id]
                        @activityId
                    [mail.activity/res_id]
                        100
                    [mail.activity/res_model]
                        res.partner
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            @testEnv
            .{Record/insert}
                [Record/models]
                    ChatterContainerComponent
                [ChatterContainerComponent/threadId]
                    100
                [ChatterContainerComponent/threadModel]
                    res.partner
            {Dev/comment}
                Update the record server side then fetch updated data in order to
                emulate what happens when using the form view.
            @testEnv
            .{Env/services}
            .{Dict/get}
                rpc
            .{Function/call}
                [model]
                    mail.activity
                [method]
                    write
                [args]
                    [0]
                        @activityId
                    [1]
                        [activity_category]
                            default
                        [activity_type_id]
                            1
            @testEnv
            .{UI/afterNextRender}
                :activity
                    {Record/findById}
                        [Activity/id]
                            @activityId
                {Activity/fetchAndUpdate}
                    @activity
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/markDoneButton}
                []
                    should have a mark done button when changing activity type from 'Upload Document' to 'Email'
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/uploadButton}
                    .{isFalsy}
                []
                    should not have an upload button after changing the activity type from 'Upload Document' to 'Email'
`;
