/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            send message only once when enter is pressed twice quickly
        [Test/model]
            DiscussComponent
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
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
                [Server/mockRPC]
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            route
                            args
                            original
                        [Function/out]
                            {if}
                                @route
                                .{=}
                                    /mail/message/post
                            .{then}
                                {Test/step}
                                    message_post
                            @original
            @testEnv
            .{Record/insert}
                [Record/models]
                    Discuss
                [Discuss/initActiveId]
                    20
            @testEnv
            .{Record/insert}
                [Record/models]
                    DiscussComponent
            {Dev/comment}
                type message
            {UI/afterNextRender}
                {UI/focus}
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            ComposerTextInputComponent
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                {UI/insertText}
                    test message
            {UI/afterNextRender}
                @testEnv
                .{Record/all}
                    [Record/models]
                        ComposerTextInputComponent
                .{Collection/first}
                .{ComposerTextInputComponent/textarea}
                .{UI/keydown}
                    [key]
                        Enter
                @testEnv
                .{Record/all}
                    [Record/models]
                        ComposerTextInputComponent
                .{Collection/first}
                .{ComposerTextInputComponent/textarea}
                .{UI/keydown}
                    [key]
                        Enter
            {Test/verifySteps}
                []
                    message_post
                []
                    The message has been posted only once
`;
