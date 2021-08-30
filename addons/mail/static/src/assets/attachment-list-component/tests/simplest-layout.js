/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            simplest layout
        [Test/model]
            AttachmentListComponent
        [Test/assertions]
            7
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
            :attachment
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Attachment
                    [Attachment/filename]
                        test.txt
                    [Attachment/id]
                        750
                    [Attachment/mimetype]
                        text/plain
                    [Attachment/name]
                        test.txt
            :message
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Message
                    [Message/attachments]
                        {Field/add}
                            @attachment
                    [Message/author]
                        @testEnv
                        .{Env/currentPartner}
                    [Message/body]
                        <p>Test</p>
                    [Message/id]
                        100
            @testEnv
            .{Record/insert}
                [Record/models]
                    MessageViewComponent
                [MessageViewComponent/messageView]
                    {Record/insert}
                        [Record/models]
                            MessageView
                        [MessageView/message]
                            @message
            :attachmentEl
                @testEnv
                .{Record/all}
                    [Record/models]
                        AttachmentListComponent
                .{Collection/first}
                .{AttachmentListComponent/nonImageAttachment}
            {Test/assert}
                []
                    @attachmentEl
                    .{AttachmentCardComponent/attachment}
                    .{=}
                        @testEnv
                        .{Record/findById}
                            [Attachment/id]
                                750
                []
                    attachment component should be linked to attachment store model
            {Test/assert}
                []
                    @attachmentEl
                    .{web.Element/title}
                    .{=}
                        test.txt
                []
                    attachment should have filename as title attribute
            {Test/assert}
                []
                    @attachmentEl
                    .{AttachmentCardComponent/image}
                []
                    attachment should have an image part
            :attachmentImage
                @attachmentEl
                .{AttachmentCardComponent/image}
            {Test/assert}
                []
                    @attachmentImage
                    .{web.Element/class}
                    .{String/includes}
                        o_image
                []
                    attachment should have o_image classname (required for mimetype.scss style)
            {Test/assert}
                []
                    @attachmentImage
                    .{web.Element/data-mimetype}
                    .{=}
                        text/plain
                []
                    attachment should have data-mimetype set (required for mimetype.scss style)
            {Test/assert}
                []
                    @attachmentImage
                    .{AttachmentCardComponent/details}
                    .{isFalsy}
                []
                    attachment should not have a details part
            {Test/assert}
                []
                    @attachmentImage
                    .{AttachmentCardComponent/aside}
                    .{isFalsy}
                []
                    attachment should not have an aside part
`;
