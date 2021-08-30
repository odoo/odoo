/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            chat window should open when receiving a new DM
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
                        mail.channel
                    [mail.channel/channel_type]
                        chat
                    [mail.channel/id]
                        11
                    [mail.channel/is_pinned]
                        false
                    [mail.channel/members]
                        [0]
                            @record
                            .{Test/data}
                            .{Data/currentPartnerId}
                        [1]
                            11
                    [mail.channel/uuid]
                        channel-11-uuid
                [1]
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        11
                [2]
                    [Record/models]
                        res.users
                    [res.users/id]
                        11
                    [res.users/partner_id]
                        11
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
                    ChatWindowManagerComponent
            {Dev/comment}
                simulate receiving the first message on channel 11
            @testEnv
            .{Component/afterNextRender}
                @env
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
                                11
                        [message_content]
                            new message
                        [uuid]
                            channel-11-uuid
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            11
                        [Thread/model]
                            mail.channel
                    .{Thread/chatWindows}
                    .{Collection/length}
                    .{=}
                        1
                []
                    chat window should be open when received a new message from new DM
`;
