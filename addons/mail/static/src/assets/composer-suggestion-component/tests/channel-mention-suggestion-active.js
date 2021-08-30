/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            channel mention suggestion active
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
                    Thread
                [ComposerSuggestionComponent/record]
                    @thread
            {Test/assert}
                []
                    @thread
                    .{Thread/composer}
                    .{Composer/composerSuggestionComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    Channel mention suggestion should be displayed
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
