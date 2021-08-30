/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            thread notifications are re-ordered on receiving a new message
        [Test/model]
            NotificationListComponent
        [Test/assertions]
            4
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
                        100
                    [mail.channel/name]
                        Channel 2019
                []
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        200
                    [mail.channel/name]
                        Channel 2020
                []
                    [Record/models]
                        mail.message
                    [mail.message/date]
                        2019-01-01 00:00:00
                    [mail.message/id]
                        42
                    [mail.message/model]
                        mail.channel
                    [mail.message/res_id]
                        100
                []
                    [Record/models]
                        mail.message
                    [mail.message/date]
                        2020-01-01 00:00:00
                    [mail.message/id]
                        43
                    [mail.message/model]
                        mail.channel
                    [mail.message/res_id]
                        200
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
                    []
                        [Record/models]
                            NotificationListView
                        [NotificationListView/filter]
                            all
                    []
                        [Record/models]
                            NotificationListComponent
                        [NotificationListComponent/notificationListView]
                            {Record/all}
                                [Record/models]
                                    NotificationListView
                            .{Collection/first}
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/threadPreview}
                    .{Collection/length}
                    .{=}
                        2
                []
                    there should be two thread previews

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    bus_service
                .{Dict/get}
                    trigger
                .{Function/call}
                    [0]
                        notification
                    [1]
                        [type]
                            mail.channel/new_message
                        [payload]
                            [id]
                                100
                            [message]
                                [author_id]
                                    [0]
                                        7
                                    [1]
                                        Demo User
                                [body]
                                    <p>New message !</p>
                                [date]
                                    2020-03-23 10:00:00
                                [id]
                                    44
                                [message_type]
                                    comment
                                [model]
                                    mail.channel
                                [record_name]
                                    Channel 2019
                                [res_id]
                                    100
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/threadPreview}
                    .{Collection/length}
                    .{=}
                        2
                []
                    there should still be two thread previews
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/threadPreview}
                    .{Collection/first}
                    .{NotificationGroupComponent/name}
                    .{web.Element/textContent}
                    .{=}
                        Channel 2019
                []
                    First channel in the list should now be 'Channel 2019'
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/threadPreview}
                    .{Collection/second}
                    .{NotificationGroupComponent/name}
                    .{web.Element/textContent}
                    .{=}
                        Channel 2020
                []
                    Second channel in the list should now be 'Channel 2020'
`;
