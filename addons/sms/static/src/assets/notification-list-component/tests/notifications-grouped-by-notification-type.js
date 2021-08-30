/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            notifications grouped by notification_type
        [Test/feature]
            sms
        [Test/model]
            NotificationListComponent
        [Test/assertions]
            11
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                []
                    {Dev/comment}
                        first message that is expected to have a failure
                    [Record/models]
                        mail.message
                    [mail.message/id]
                        11
                        {Dev/comment}
                            random unique id, will be used to link failure to message
                    [mail.message/message_type]
                        sms
                        {Dev/comment}
                            different type from second message
                    [mail.message/model]
                        res.partner
                        {Dev/comment}
                            same model as second message (and not 'mail.channel')
                    [mail.message/res_id]
                        31
                        {Dev/comment}
                            same res_id as second message
                    [mail.message/res_model_name]
                        Partner
                        {Dev/comment}
                            random related model name
                []
                    {Dev/comment}
                        second message that is expected to have a failure
                    [Record/models]
                        mail.message
                    [mail.message/id]
                        12
                        {Dev/comment}
                            random unique id, will be used to link failure to message
                    [mail.message/message_type]
                        email
                        {Dev/comment}
                            different type from first message
                    [mail.message/model]
                        res.partner
                        {Dev/comment}
                            same model as first message (and not 'mail.channel')
                    [mail.message/res_id]
                        31
                        {Dev/comment}
                            same res_id as first message
                    [mail.message/res_model_name]
                        Partner
                        {Dev/comment}
                            same related model name for consistency
                []
                    {Dev/comment}
                        first failure that is expected to be used in the test
                    [Record/models]
                        mail.notification
                    [mail.notification/mail_message_id]
                        11
                        {Dev/comment}
                            id of the related first message
                    [mail.notification/notification_status]
                        exception
                        {Dev/comment}
                            necessary value to have a failure
                    [mail.notification/notification_type]
                        sms
                        {Dev/comment}
                            different type from second failure
                []
                    {Dev/comment}
                        second failure that is expected to be used in the test
                    [Record/models]
                        mail.notification
                    [mail.notification/mail_message_id]
                        12
                        {Dev/comment}
                            id of the related second message
                    [mail.notification/notification_status]
                        exception
                        {Dev/comment}
                            necessary value to have a failure
                    [mail.notification/notification_type]
                        email
                        {Dev/comment}
                            different type from first failure
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
                    NotificationListComponent
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            NotificationListComponent
                    .{Collection/first}
                    .{NotificationListComponent/group}
                    .{Collection/length}
                    .{=}
                        2
                []
                    should have 2 notifications group
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            NotificationListComponent
                    .{Collection/first}
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/name}
                []
                    should have 1 group name in first group
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            NotificationListComponent
                    .{Collection/first}
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/name}
                    .{web.Element/textContent}
                    .{=}
                        Partner
                []
                    should have model name as group name
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            NotificationListComponent
                    .{Collection/first}
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/counter}
                []
                    should have 1 group counter in first group
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            NotificationListComponent
                    .{Collection/first}
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/counter}
                    .{web.Element/textContent}
                    .{=}
                        (1)
                []
                    should have 1 notification in first group
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/trais]
                            NotificationListComponent
                    .{Collection/first}
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
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            NotificationListComponent
                    .{Collection/first}
                    .{NotificationListComponent/group}
                    .{Collection/second}
                    .{NotificationGroupComponent/name}
                []
                    should have 1 group name in second group
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            NotificationListComponent
                    .{Collection/first}
                    .{NotificationListComponent/group}
                    .{Collection/second}
                    .{NotificationGroupComponent/name}
                    .{web.Element/textContent}
                    .{=}
                        Partner
                []
                    should have second model name as group name
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            NotificationListComponent
                    .{Collection/first}
                    .{NotificationListComponent/group}
                    .{Collection/second}
                    .{NotificationGroupComponent/counter}
                []
                    should have 1 group counter in second group
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            NotificationListComponent
                    .{Collection/first}
                    .{NotificationListComponent/group}
                    .{Collection/second}
                    .{NotificationGroupComponent/counter}
                    .{web.Element/textContent}
                    .{=}
                        (1)
                []
                    should have 1 notification in second group
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            NotificationListComponent
                    .{Collection/first}
                    .{NotificationListComponent/group}
                    .{Collection/second}
                    .{NotificationGroupComponent/inlineText}
                    .{web.Element/textContent}
                    .{=}
                        An error occurred when sending an SMS.
                []
                    should have the group text corresponding to sms
`;
