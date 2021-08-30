/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            chat window should remain folded when new message is received
        [Test/model]
            ChatWindowManagerComponent
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
                        res.partner
                    [res.partner/id]
                        10
                    [res.partner/name]
                        Demo
                [1]
                    [Record/models]
                        res.users
                    [res.users/id]
                        42
                    [res.users/name]
                        Foreigner user
                    [res.users/partner_id]
                        10
                [2]
                    [Record/models]
                        mail.channel
                    [mail.channel/channel_type]
                        chat
                    [mail.channel/id]
                        10
                    [mail.channel/is_minimized]
                        true
                    [mail.channel/is_pinned]
                        false
                    [mail.channel/members]
                        [0]
                            @record
                            .{Test/data}
                            .{Data/currentPartnerId}
                        [1]
                            10
                    [mail.channel/state]
                        folded
                    [mail.channel/uuid]
                        channel-10-uuid
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            {Dev/comment}
                simulate receiving a new message
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    rpc
                .{Function/call}
                    [route]
                        /mail/chat_post
                    [params]
                        [context]
                            [mockedUserId]
                                42
                        [message_content]
                            New Message 2
                        [uuid]
                            channel-10-uuid
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            10
                        [Thread/model]
                            mail.channel
                    .{Thread/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/isFolded}
                []
                    chat window should remain folded
`;
