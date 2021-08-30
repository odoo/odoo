/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            view attachment
        [Test/model]
            AttachmentListComponent
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
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            @testEnv
            .{Record/insert}
                [Record/models]
                    DialogManagerComponent
            :attachment
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Attachment
                    [Attachment/filename]
                        test.png
                    [Attachment/id]
                        750
                    [Attachment/mimetype]
                        image/png
                    [Attachment/name]
                        test.png
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
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            AttachmentImageComponent
                    .{Collection/first}
                    .{AttachmentImageComponent/image}
                []
                    attachment should have an image part

            @testEnv
            .{UI/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            AttachmentImageComponent
                    .{Collection/first}
            {Test/assert}
                []
                    @testEnv
                    .{DialogManager/dialogs}
                    .{Collection/length}
                    .{=}
                        1
                []
                    a dialog should have been opened once attachment image is clicked
            {Test/assert}
                []
                    @testEnv
                    .{DialogManager/dialogs}
                    .{Collection/first}
                    .{Dialog/attachmentViewer}
                []
                    an attachment viewer should have been opened once attachment image is clicked
`;
