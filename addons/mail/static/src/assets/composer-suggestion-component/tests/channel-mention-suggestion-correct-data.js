/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            channel mention suggestion correct data
        [Test/model]
            ComposerSuggestionComponent
        [Test/assertions]
            3
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
                [mail.channel/name]
                    General
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
                    Channel mention suggestion should be present
            {Test/assert}
                []
                    @thread
                    .{Thread/composer}
                    .{Composer/composerSuggestionComponents}
                    .{Collection/first}
                    .{ComposerSuggestionComponent/part1}
                []
                    Channel name should be present
            {Test/assert}
                []
                    @thread
                    .{Thread/composer}
                    .{Composer/composerSuggestionComponents}
                    .{Collection/first}
                    .{ComposerSuggestionComponent/part1}
                    .{web.Element/textContent}
                    .{=}
                        General
                []
                    Channel name should be displayed
`;
