/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            ODT file is not viewable
        [Test/model]
            AttachmentListComponent
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
                        test.odt
                    [Attachment/id]
                        750
                    [Attachment/mimetype]
                        application/vnd.oasis.opendocument.text
                    [Attachment/name]
                        test.odt
            :message
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Message
                    [Message/attachments]
                        {Field/adds}
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
                    @message
                    .{Message/attachments}
                    .{Collection/first}
                    .{Attachment/isViewable}
                    .{isFalsy}
                []
                    should not be viewable
`;
