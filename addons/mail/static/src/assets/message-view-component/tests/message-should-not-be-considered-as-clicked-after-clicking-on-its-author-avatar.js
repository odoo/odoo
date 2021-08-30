/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            message should not be considered as "clicked" after clicking on its author avatar
        [Test/model]
            MessageViewComponent
        [Test/assertions]
            1
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            :message
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Message
                    [Message/author]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                Partner
                            [Partner/displayName]
                                Demo User
                            [Partner/id]
                                7
                    [Message/body]
                        <p>Test</p>
                    [Message/id]
                        100
            @testEnv
            .{Record/insert}
                [Record/models]
                    MessageViewComponent
                [MessageViewComponent/message]
                    @message
            @testEnv
            .{UI/click}
                @message
                .{Message/messageComponents}
                .{Collection/first}
                .{MessageViewComponent/authorAvatar}
            {Utils/nextAnimationFrame}
            {Test/assert}
                []
                    @message
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/isClicked}
                    .{isFalsy}
                []
                    message should not be considered as 'clicked' after clicking on its author avatar
`;
