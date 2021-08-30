/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            composer state: attachments save and restore
        [Test/model]
            DiscussComponent
        [Test/assertions]
            6
        [Test/scenario]
            {Dev/comment}
                channels expected to be found in the sidebar
                with random unique id and name that will be referenced in the test
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [0]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        20
                    [mail.channel/name]
                        General
                [1]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        21
                    [mail.channel/name]
                        Special
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
                    DiscussComponent
            @testEnv
            .{Thread/open}
                @testEnv
                .{Record/findById}
                    [Thread/id]
                        20
                    [Thread/model]
                        mail.channel
            {Dev/comment}
                Add attachment in a message for #general
            @testEnv
            .{Component/afterNextRender}
                    :file
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                web.File
                            [web.File/content]
                                hello, world
                            [web.File/contentType]
                                text/plain
                            [web.File/name]
                                text.txt
                    @testEnv
                    .{UI/inputFiles}
                        [0]
                            @testEnv
                            .{Discuss/threadView}
                            .{ThreadView/composerView}
                            .{ComposerView/fileUploader}
                            .{FileUploader/fileInput}
                        [1]
                            @file
            {Dev/comment}
                Switch to #special
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/itemChannel}
                    .{Collection/second}
            {Dev/comment}
                Add attachments in a message for #special
            :files
                {Record/insert}
                    [Record/models]
                        Collection
                    [0]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                web.File
                            [web.File/content]
                                hello2, world
                            [web.File/contentType]
                                text/plain
                            [web.File/name]
                                text2.txt
                    [1]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                web.File
                            [web.File/content]
                                hello3, world
                            [web.File/contentType]
                                text/plain
                            [web.File/name]
                                text3.txt
                    [2]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                web.File
                            [web.File/content]
                                hello4, world
                            [web.File/contentType]
                                text/plain
                            [web.File/name]
                                text4.txt
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/inputFiles}
                    [0]
                        @testEnv
                        .{Discuss/threadView}
                        .{ThreadView/composerView}
                        .{ComposerView/fileUploader}
                        .{FileUploader/fileInput}
                    [1]
                        @files
            {Dev/comment}
                Switch back to #general
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/itemChannel}
                    .{Collection/first}
            {Dev/comment}
                Check attachment is reloaded
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/attachments}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have 1 attachment in the composer
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/attachments}
                    .{Collection/first}
                    .{=}
                        @testEnv
                        .{Record/findById}
                            [Attachment/id]
                                1
                []
                    should have correct 1st attachment in the composer

            {Dev/comment}
                Switch back to #special
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/itemChannel}
                    .{Collection/second}
            {Dev/comment}
                Check attachments are reloaded
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/attachments}
                    .{Collection/length}
                    .{=}
                        3
                []
                    should have 3 attachments in the composer
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/attachments}
                    .{Collection/first}
                    .{=}
                        @testEnv
                        .{Record/findById}
                            [Attachment/id]
                                2
                []
                    should have attachment with id 2 as 1st attachment
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/attachments}
                    .{Collection/second}
                    .{=}
                    @testEnv
                    .{Record/findById}
                        [Attachment/id]
                            3
                []
                    should have attachment with id 3 as 2nd attachment
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/attachments}
                    .{Collection/third}
                    .{=}
                        @testEnv
                        .{Record/findById}
                            [Attachment/id]
                                4
                []
                    should have attachment with id 4 as 3rd attachment
`;
