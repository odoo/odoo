/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            do not post message with "Enter"
        [Test/model]
            ChatterComponent
        [Test/assertions]
            2
        [Test/scenario]
            {Dev/comment}
                Note that test doesn't assert Enter makes a newline, because this
                default browser cannot be simulated with just dispatching
                programmatically crafted events...
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    res.partner
                [res.partner/id]
                    100
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
                    ChatterContainerComponent
                [ChatterContainerComponent/threadId]
                    100
                [ChatterContainerComponent/threadModel]
                    res.partner
            {Test/assert}
                []
                    @chatter
                    .{Chatter/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/length}
                    .{=}
                        0
                []
                    should not have any message initially in chatter

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @chatter
                    .{Chatter/chatterTopbarComponents}
                    .{Collection/first}
                    .{ChatterTopbarComponent/buttonSendMessage}
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/focus}
                    @chatter
                    .{Chatter/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                @testEnv
                .{UI/insertText}
                    Test
            @testEnv
            .{UI/keydown}
                [0]
                    @chatter
                    .{Chatter/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                [1]
                    [key]
                        Enter
            {Utils/nextAnimationFrame}
            {Test/assert}
                []
                    @chatter
                    .{Chatter/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/length}
                    .{=}
                        0
                []
                    should still not have any message in mailing channel after pressing 'Enter' in text input of composer
`;
