/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            warning on send with shortcut when attempting to post message with still-uploading attachments
        [Test/model]
            DiscussComponent
        [Test/assertions]
            7
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/owlEnv]
                        [services]
                            [notification]
                                [notify]
                                    {Record/insert}
                                        [Record/models]
                                            Function
                                        [Function/in]
                                            params
                                        [Function/out]
                                            {Test/assert}
                                                []
                                                    @params
                                                    .{Dict/get}
                                                        message
                                                    .{=}
                                                        Please wait while the file is uploading.
                                                []
                                                    notification content should be about the uploading file
                                            {Test/assert}
                                                []
                                                    @params
                                                    .{Dict/get}
                                                        type
                                                    .{=}
                                                        warning
                                                []
                                                    notification should be a warning
                                            {Test/step}
                                                notification
            @testEnv
            .{Record/insert}
                []
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        10
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
                [Server/mockFetch]
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            resource
                            init
                            original
                        [Function/out]
                            :res
                                @original
                            {if}
                                @resource
                                .{=}
                                    /mail/attachment/upload
                            .{then}
                                {Dev/comment}
                                    simulates attachment is never finished uploading
                                {Promise/await}
                            @original
            @testEnv
            .{Record/insert}
                [Record/models]
                    Discuss
                [Discuss/initActiveId]
                    10
            @testEnv
            .{Record/insert}
                [Record/models]
                    DiscussComponent
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
            .{UI/afterNextRender}
                {UI/inputFiles}
                    []
                        @testEnv
                        .{Discuss/threadView}
                        .{ThreadView/composerView}
                        .{ComposerView/fileUploader}
                        .{FileUploader/fileInput}
                    []
                        @file

            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            AttachmentCardComponent
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have only one attachment
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            AttachmentCardComponent
                    .{Collection/first}
                    .{AttachmentCardComponent/attachmendCard}
                    .{AttachmentCard/attachment}
                    .{Attachment/isUploading}
                []
                    attachment displayed is being uploaded
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            ComposerComponent
                    .{Collection/first}
                    .{ComposerComponent/buttonSend}
                []
                    composer send button should be displayed

            {Dev/comment}
                Try to send message
            {UI/keydown}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            ComposerTextInputComponent
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                []
                    [key]
                        Enter
            {Test/verifySteps}
                []
                    notification
                []
                    should have triggered a notification for inability to post message at the moment (some attachments are still being uploaded)
`;
