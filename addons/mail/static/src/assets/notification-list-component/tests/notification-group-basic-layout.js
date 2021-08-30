/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            notification group basic layout
        [Test/model]
            NotificationListComponent
        [Test/assertions]
            10
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
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
                        email
                        {Dev/comment}
                            message must be email (goal of the test)
                    [mail.message/model]
                        mail.channel
                        {Dev/comment}
                            expected value to link message to channel
                    [mail.message/res_id]
                        31
                        {Dev/comment}
                            id of a random channel
                    [mail.message/res_model_name]
                        Channel
                        {Dev/comment}
                            random res model name, will be asserted in the test
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
                        email
                        {Dev/comment}
                            expected failure type for email message
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
                        1
                []
                    should have 1 notification group
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/name}
                []
                    should have 1 group name
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/name}
                    .{web.Element/textContent}
                    .{=}
                        Channel
                []
                    should have model name as group name
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/counter}
                []
                    should have 1 group counter
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/counter}
                    .{web.Element/textContent}
                    .{=}
                        (1)
                []
                    should have only 1 notification in the group
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/date}
                []
                    should have 1 group date
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/date}
                    .{web.Element/textContent}
                    .{=}
                        a few seconds ago
                []
                    should have the group date corresponding to now
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/inlineText}
                []
                    should have 1 group text
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/inlineText}
                    .{web.Element/textContent}
                    .{=}
                        An error occurred when sending an email.
                []
                    should have the group text corresponding to email
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/markAsRead}
                []
                    should have 1 mark as read button
`;
