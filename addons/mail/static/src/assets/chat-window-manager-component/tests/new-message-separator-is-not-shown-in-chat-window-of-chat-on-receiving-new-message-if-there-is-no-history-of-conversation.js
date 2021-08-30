/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            new message separator is not shown in a chat window of a chat on receiving new message if there is no history of conversation
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
                        10
                    [mail.channel/members]
                        [0]
                            @record
                            .{Test/data}
                            .{Data/currentPartnerId}
                        [1]
                            10
                    [mail.channel/uuid]
                        channel-10-uuid
                [1]
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        10
                    [res.partner/name]
                        Demo
                [2]
                    [Record/models]
                        res.users
                    [res.users/id]
                        42
                    [res.users/name]
                        Foreigner user
                    [res.users/partner_id]
                        10
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            {Dev/comment}
                simulate receiving a message
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
                            hu
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
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/messageListComponents}
                    .{Collection/first}
                    .{MessageListComponent/separatorNewMessages}
                    .{isFalsy}
                []
                    should not display 'new messages' separator in the conversation of a chat on receiving new message if there is no history of conversation
`;
