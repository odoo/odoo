/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            receive other member typing status "is typing"
        [Test/model]
            ThreadTextualTypingStatusComponent
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
                    ThreadTextualTypingStatusComponent
                [ThreadTextualTypingStatusComponent/thread]
                    @thread
            {Test/assert}
                []
                    @thread
                    .{Thread/threadTextualTypingStatusComponents}
                    .{Collection/first}
                    .{web.Element/textContent}
                    .{=}
                        {String/empty}
                []
                    Should display no one is currently typing

            {Dev/comment}
                simulate receive typing notification from demo
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
                    .{Thread/threadTextualTypingStatusComponents}
                    .{Collection/first}
                    .{web.Element/textContent}
                    .{=}
                        Demo is typing...
                []
                    Should display that demo user is typing
`;
