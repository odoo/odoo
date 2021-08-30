/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            mark as read
        [Test/feature]
            sms
        [Test/model]
            NotificationListComponent
        [Test/assertions]
            6
        [Test/scenario]
            :bus
                {Record/insert}
                    [Record/models]
                        Bus
            {Bus/on}
                [0]
                    @bus
                [1]
                    do-action
                [2]
                    null
                [3]
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            payload
                        [Function/out]
                            {Test/step}
                                do_action
                            {Test/assert}
                                []
                                    @payload
                                    .{Dict/get}
                                        action
                                    .{=}
                                        sms.sms_cancel_action
                                []
                                    action should be the one to cancel sms
                            {Test/assert}
                                []
                                    @payload
                                    .{Dict/get}
                                        options
                                    .{Dict/get}
                                        additional_context
                                    .{Dict/get}
                                        default_model
                                    .{=}
                                        mail.channel
                                []
                                    action should have the group model as default_model
                            {Test/assert}
                                []
                                    @payload
                                    .{Dict/get}
                                        options
                                    .{Dict/get}
                                        additional_context
                                    .{Dict/get}
                                        unread_counter
                                    .{=}
                                        1
                                []
                                    action should have the group notification length as unread_counter
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/owlEnv]
                        [bus]
                            @bus
            @testEnv
            .{Record/insert}
                []
                    {Dev/comment}
                        message that is expected to have a failure
                    [Record/models]
                        mail.message
                    [mail.message/id]
                        11
                        {Dev/comment}
                            random unique id, will be used to link failure to message
                    [mail.message/message_type]
                        sms
                        {Dev/comment}
                            message must be sms (goal of the test)
                    [mail.message/model]
                        mail.channel
                        {Dev/comment}
                            expected value to link message to channel
                    [mail.message/res_id]
                        31
                        {Dev/comment}
                            id of a random channel
                []
                    {Dev/comment}
                        failure that is expected to be used in the test
                    [Record/models]
                        mail.notification
                    [mail.notification/mail_message_id]
                        11
                        {Dev/comment}
                            id of the related message
                    [mail.notification/notification_status]
                        exception
                        {Dev/comment}
                            necessary value to have a failure
                    [mail.notification/notification_type]
                        sms
                        {Dev/comment}
                            expected failure type for sms message
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @recod
                    .{Test/data}
            @testEnv
            .{Record/insert}
                [Record/models]
                    NotificationListComponent
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            NotificationListComponent
                    .{Collection/first}
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/markAsRead}
                []
                    should have 1 mark as read button

            @testEnv
            .{UI/click}
                @testEnv
                .{Record/all}
                    [Record/models]
                        NotificationListComponent
                .{Collection/first}
                .{NotificationListComponent/group}
                .{Collection/first}
                .{NotificationGroupComponent/markAsRead}
            {Test/verifySteps}
                []
                    do_action
                []
                    should do an action to display the cancel sms dialog
`;
