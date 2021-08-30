/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            non-failure notifications are ignored
        [Test/model]
            NotificationListComponent
        [Test/assertions]
            1
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                []
                    {Dev/comment}
                        message that is expected to have a notification
                    [Record/models]
                        mail.message
                    [mail.message/id]
                        11
                        {Dev/comment}
                            random unique id, will be used to link failure to message
                    [mail.message/message_type]
                        email
                        {Dev/comment}
                            message must be email (goal of the test)
                    [mail.message/model]
                        res.partner
                        {Dev/comment}
                            random model
                    [mail.message/res_id]
                        31
                        {Dev/comment}
                            random unique id, useful to link failure to message
                []
                    {Dev/comment}
                        notification that is expected to be used in the test
                    [Record/models]
                        mail.notification
                    [mail.notification/mail_message_id]
                        11
                        {Dev/comment}
                            id of the related first message
                    [mail.notification/notification_status]
                        ready
                        {Dev/comment}
                            non-failure status
                    [mail.notification/notification_type]
                        email
                        {Dev/comment}
                            expected notification type for email message
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            :notificationListComponent
                @testEnv
                .{Record/insert}
                    [Record/models]
                        NotificationListComponent
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/group}
                    .{Collection/length}
                    .{=}
                        0
                []
                    should have 0 notification group
`;
