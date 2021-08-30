/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            prevent attachment delete on non-authored message
        [Test/model]
            MessageViewComponent
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
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            :message
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Message
                    [Message/attachments]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                Attachment
                            [Attachment/filename]
                                BLAH.jpg
                            [Attachment/id]
                                10
                            [Attachment/name]
                                BLAH
                            [Attachment/mimetype]
                                image/jpeg
                    [Message/author]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                Partner
                            [Partner/displayName]
                                Guy
                            [Partner/id]
                                11
                    [Message/body]
                        <p>Test</p>
                    [Message/id]
                        100
            @testEnv
            .{Record/insert}
                [Record/models]
                    MessageViewComponent
                [MessageViewComponent/message]
                    @message
            {Test/assert}
                []
                    @message
                    .{Message/attachments}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have an attachment
            {Test/assert}
                []
                    @message
                    .{Message/attachments}
                    .{Collection/first}
                    .{Attachment/attachmentImages}
                    .{Collection/first}
                    .{AttachmentImage/attachmentImageComponents}
                    .{Collection/first}
                    .{AttachmentImageComponent/asideItemUnlink}
                    .{isFalsy}
                []
                    delete attachment button should not be printed
`;
