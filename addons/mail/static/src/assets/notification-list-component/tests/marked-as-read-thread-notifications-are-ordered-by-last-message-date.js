/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            marked as read thread notifications are ordered by last message date
        [Test/model]
            NotificationListComponent
        [Test/assertions]
            3
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
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/threadPreview}
                    .{Collection/first}
                    .{web.Element/textContent}
                    .{=}
                        Channel 2020
                []
                    First channel in the list should be the channel of 2020 (more recent last message)
            {Test/assert}
                []
                    @notificationListComponent
                    .{NotificationListComponent/threadPreview}
                    .{Collection/second}
                    .{web.Element/textContent}
                    .{=}
                        Channel 2019
                []
                    Second channel in the list should be the channel of 2019 (least recent last message)
`;
