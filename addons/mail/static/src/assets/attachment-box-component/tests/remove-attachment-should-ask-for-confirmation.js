/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            remove attachment should ask for confirmation
        [Test/model]
            AttachmentBoxComponent
        [Test/assertions]
            5
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                []
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        100
                []
                    [Record/models]
                        ir.attachment
                    [ir.attachment/id]
                        143
                    [ir.attachment/mimetype]
                        text/plain
                    [ir.attachment/name]
                        Blah.txt
                    [ir.attachment/res_id]
                        100
                    [ir.attachment/res_model]
                        res.partner
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
            @testEnv
            .{Record/insert}
                [Record/models]
                    ChatterContainerComponent
                [ChatterContainerComponent/isAttachmentBoxVisibleInitially]
                    true
                [ChatterContainerComponent/threadId]
                    100
                [ChatterContainerComponent/threadModel]
                    res.partner
            @testEnv
            .{Record/insert}
                [Record/models]
                    AttachmentBoxComponent
                [AttachmentBoxComponent/attachmentBoxView]
                    @chatter
                    .{Chatter/attachmentBoxView}
            {Test/assert}
                []
                    @thread
                    .{Thread/attachments}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have an attachment
            {Test/assert}
                []
                    @thread
                    .{Thread/attachments}
                    .{Collection/first}
                    .{Attachment/attachmentCards}
                    .{Collection/first}
                    .{AttachmentCard/attachmentCardComponents}
                    .{Collection/first}
                    .{AttachmentCardComponent/asideItemUnlink}
                []
                    attachment should have a delete button

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @thread
                    .{Thread/attachments}
                    .{Collection/first}
                    .{Attachment/attachmentCards}
                    .{Collection/first}
                    .{AttachmentCard/attachmentCardComponents}
                    .{Collection/first}
                    .{AttachmentCardComponent/asideItemUnlink}
            {Test/assert}
                []
                    @thread
                    .{Thread/attachments}
                    .{Collection/first}
                    .{Attachment/attachmentDeleteConfirmComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    A confirmation dialog should have been opened
            {Test/assert}
                []
                    @thread
                    .{Thread/attachments}
                    .{Collection/first}
                    .{Attachment/attachmentDeleteConfirmComponents}
                    .{Collection/first}
                    .{AttachmentDeleteConfirmComponent/mainText}
                    .{web.Element/textContent}
                    .{=}
                        Do you really want to delete "Blah.txt"?
                []
                    Confirmation dialog should contain the attachment delete confirmation text

            {Dev/comment}
                Confirm the deletion
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @thread
                    .{Thread/attachments}
                    .{Collection/first}
                    .{Attachment/attachmentDeleteConfirmComponents}
                    .{Collection/first}
                    .{AttachmentDeleteConfirmComponent/confirmButton}
            {Test/assert}
                []
                    @thread
                    .{Thread/attachments}
                    .{Collection/length}
                    .{=}
                        0
                []
                    should no longer have an attachment
`;
