/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            canned response suggestion displayed
        [Test/model]
            ComposerSuggestionComponent
        [Test/assertions]
            2
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
            :cannedResponse
                @testEnv
                .{Record/insert}
                    [Record/models]
                        CannedResponse
                    [CannedResponse/id]
                        7
                    [CannedResponse/source]
                        hello
                    [CannedResponse/substitution]
                        Hello, how are you?
            @testEnv
            .{Record/insert}
                [Record/models]
                    ComposerSuggestionComponent
                [ComposerSuggestionComponent/composer]
                    @thread
                    .{Thread/composer}
                [ComposerSuggestionComponent/isActive]
                    true
                [ComposerSuggestionComponent/modelName]
                    CannedResponse
                [ComposerSuggestionComponent/record]
                    @cannedResponse
            {Test/assert}
                []
                    @thread
                    .{Thread/composer}
                    .{Composer/composerSuggestionComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    Canned response suggestion should be displayed
            {Test/assert}
                []
                    @thread
                    .{Thread/composer}
                    .{Composer/composerSuggestionComponents}
                    .{Collection/first}
                    .{ComposerSuggestionComponent/isActive}
                []
                    should be active initially
`;
