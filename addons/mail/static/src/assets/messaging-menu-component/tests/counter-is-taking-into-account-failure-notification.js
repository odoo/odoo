/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            counter is taking into account failure notification
        [Test/model]
            MessagingMenuComponent
        [Test/assertions]
            2
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                []
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        31
                    [mail.channel/seen_message_id]
                        11
                []
                    {Dev/comment}
                        message that is expected to have a failure
                    [Record/models]
                        mail.message
                    [mail.message/id]
                        11
                        {Dev/comment}
                            random unique id, will be used to link failure to message
                    [mail.message/model]]
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
                    [mail.notification/notification_type]
                        email
                    [mail.notification/mail_message_id]
                        11
                        {Dev/comment}
                            id of the related message
                    [mail.notification/notification_status]
                        exception
                        {Dev/comment}
                            necessary value to have a failure
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
                    MessagingMenuComponent
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/counter}
                []
                    should display a notification counter next to the messaging menu for one notification
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/counter}
                    .{web.Element/textContent}
                    .{=}
                        1
                []
                    should display a counter of '1' next to the messaging menu
`;
