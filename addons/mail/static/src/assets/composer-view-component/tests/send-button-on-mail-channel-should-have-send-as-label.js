/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            send button on mail.channel should have "Send" as label
        [Test/model]
            ComposerViewComponent
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
                    ComposerViewComponent
                [ComposerViewComponent/composerView]
                    {Record/insert}
                        [Record/models]
                            ComposerView
                        [ComposerView/composer]
                            @thread
                            .{Thread/composer}
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            ComposerViewComponent
                    .{Collection/first}
                    .{ComposerViewComponent/buttonSend}
                    .{web.Element/textContent}
                    .{=}
                        Send
                []
                    Send button of mail.channel composer should have 'Send' as label
`;
