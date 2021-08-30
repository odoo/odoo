/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the attachments to be displayed by this attachment list.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachments
        [Field/model]
            AttachmentList
        [Field/type]
            many
        [Field/target]
            Attachment
        [Field/inverse]
            Attachment/attachmentLists
        [Field/compute]
            {if}
                @record
                .{AttachmentList/messageViewOwner}
            .{then}
                @record
                .{AttachmentList/messageViewOwner}
                .{MessageView/message}
                .{Message/attachments}
            .{elif}
                @record
                .{AttachmentList/attachmentBoxViewOwner}
            .{then}
                @record
                .{AttachmentList/attachmentBoxViewOwner}
                .{AttachmentBoxView/chatter}
                .{Chatter/thread}
                .{Thread/allAttachments}
            .{elif}
                @record
                .{AttachmentList/composerViewOwner}
                .{&}
                    @record
                    .{AttachmentList/composerViewOwner}
                    .{ComposerView/composer}
            .{then}
                @record
                .{AttachmentList/composerViewOwner}
                .{ComposerView/composer}
                .{Composer/attachments}
            .{else}
                {Record/empty}
`;
