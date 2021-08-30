/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            livechat: no add attachment button
        [Test/feature]
            hr_holidays
        [Test/model]
            ComposerViewComponent
        [Test/assertions]
            2
        [Test/scenario]
            {Dev/comment}
                Attachments are not yet supported in livechat, especially from livechat
                visitor PoV. This may likely change in the future with task-2029065.
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
            :thread
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Thread
                    [Thread/channelType]
                        livechat
                    [Thread/id]
                        10
                    [Thread/model]
                        mail.channel
            @testEnv
            .{Record/insert}
                [Record/models]
                    ComposerViewComponent
                [ComposerViewComponent/composer]
                    @thread
                    .{Thread/composer}
            {Test/assert}
                []
                    @thread
                    .{Thread/composer}
                    .{Composer/composerViewComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have a composer
            {Test/assert}
                []
                    @thread
                    .{Thread/composer}
                    .{Composer/composerViewComponents}
                    .{Collection/first}
                    .{ComposerViewComponent/buttonAttachment}
                    .{isFalsy}
                []
                    composer linked to livechat should not have a 'Add attachment' button
`;
