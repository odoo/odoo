/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            should not be able to reply to temporary/transient messages
        [Test/model]
            DiscussComponent
        [Test/assertions]
            1
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
                these user interactions is to forge a transient message response from channel command "/who"
            @testEnv
            .{UI/afterNextRender}
                @testEnv
                .{UI/focus}
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            ComposerTextInputComponent
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                @testEnv
                .{UI/insertText}
                    /who
            @testEnv
            .{UI/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            ComposerViewComponent
                    .{Collection/first}
                    .{ComposerView/buttonSend}
            {Dev/comment}
                click on message to show actions on the transient message resulting from the "/who" command
            @testEnv
            .{UI/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            MessageViewComponent
                    .{Collection/first}
            {Test/assert}
                []
                    @testEnv
                    .{Record.all}
                        [Record/models]
                            MessageActionListComponent
                    .{Collection/first}
                    .{MessageActionListComponent/actionReply}
                    .{isFalsy}
                []
                    should not have action to reply to temporary/transient messages
`;
