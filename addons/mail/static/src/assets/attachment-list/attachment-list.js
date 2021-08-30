/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            AttachmentList
        [Model/fields]
            attachmentBoxViewOwner
            attachmentCards
            attachmentImages
            attachmentListViewDialog
            attachments
            composerViewOwner
            imageAttachments
            message
            messageViewOwner
            nonImageAttachments
            selectedAttachment
            viewableAttachments
        [Model/id]
            AttachmentList/composerViewOwner
            .{|}
                AttachmentList/messageViewOwner
            .{|}
                AttachmentList/attachmentBoxViewOwner
        [Model/actions]
            AttachmentList/selectNextAttachment
            AttachmentList/selectPreviousAttachment
`;
