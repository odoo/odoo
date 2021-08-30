/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            chat: correspondent is typing
        [Test/model]
            ThreadIconComponent
        [Test/assertions]
            5
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
                    [mail.channel/channel_type]
                        chat
                    [mail.channel/id]
                        20
                    [mail.channel/members]
                        [0]
                            @record
                            .{Test/data}
                            .{Data/currentPartnerId}
                        [1]
                            17
                []
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        17
                    [res.partner/im_status]
                        online
                    [res.partner/name]
                        Demo
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            :thread
                @testEnv
                .{Record/findById}
                    [Thread/id]
                        20
                    [Thread/model]
                        mail.channel
            @testEnv
            .{Record/insert}
                [Record/models]
                    ThreadIconComponent
                [ThreadIconComponent/thread]
                    @thread
            {Test/assert}
                []
                    @thread
                    .{Thread/threadIconComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have thread icon
            {Test/assert}
                []
                    @thread
                    .{Thread/threadIconComponents}
                    .{Collection/first}
                    .{ThreadIconComponent/online}
                []
                    should have thread icon with partner im status icon 'online'

            {Dev/comment}
                simulate receive typing notification from demo "is typing"
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
                            mail.channel.partner/typing_status
                        [payload]
                            [channel_id]
                                20
                            [is_typing]
                                true
                            [partner_id]
                                17
                            [partner_name]
                                Demo
            {Test/assert}
                []
                    @thread
                    .{Thread/threadIconComponents}
                    .{Collection/first}
                    .{ThreadIconComponent/typing}
                []
                    should have thread icon with partner currently typing
            {Test/assert}
                []
                    @thread
                    .{Thread/threadIconComponents}
                    .{Collection/first}
                    .{ThreadIconComponent/typing}
                    .{web.Element/title}
                    .{=}
                        Demo is typing...
                []
                    title of icon should tell demo is currently typing

            {Dev/comment}
                simulate receive typing notification from demo "no longer is typing"
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
                            mail.channel.partner/typing_status
                        [payload]
                            [channel_id]
                                20
                            [is_typing]
                                false
                            [partner_id]
                                17
                            [partner_name]
                                Demo
            {Test/assert}
                []
                    @thread
                    .{Thread/threadIconComponents}
                    .{Collection/first}
                    .{ThreadIconComponent/online}
                []
                    should have thread icon with partner im status icon 'online' (no longer typing)
`;
