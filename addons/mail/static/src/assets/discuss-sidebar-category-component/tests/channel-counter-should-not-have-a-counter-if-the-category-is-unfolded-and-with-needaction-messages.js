/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            channel - counter: should not have a counter if the category is unfolded and with needaction messages
        [Test/model]
            DiscussSidebarCategoryComponent
        [Test/assertions]
            1
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [0]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        20
                [1]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        30
                [2]
                    [Record/models]
                        mail.message
                    [mail.message/body]
                        message 1
                    [mail.message/id]
                        100
                    [mail.message/model]
                        mail.channel
                    [mail.message/res_id]
                        20
                [3]
                    [Record/models]
                        mail.message
                    [mail.message/body]
                        message 2
                    [mail.message/id]
                        200
                    [mail.message/model]
                        mail.channel
                    [mail.message/res_id]
                        30
                [4]
                    [Record/models]
                        mail.notification
                    [mail.notification/notification_type]
                        inbox
                    [mail.notification/mail_message_id]
                        100
                    [mail.notification/res_partner_id]
                        @record
                        .{Test/data}
                        .{Data/currentPartnerId}
                [5]
                    [Record/models]
                        mail.notification
                    [mail.notification/notification_type]
                        inbox
                    [mail.notification/mail_message_id]
                        200
                    [mail.notification/res_partner_id]
                        @record
                        .{Test/data}
                        .{Data/currentPartnerId}
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/categoryChannel}
                    .{DiscussSidebarCategory/counter}
                    .{=}
                        0
                []
                    should not have a counter if the category is unfolded and with needaction messages
`;
