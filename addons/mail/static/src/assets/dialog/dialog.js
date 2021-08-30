/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            Dialog
        [Model/fields]
            attachmentCardOwnerAsAttachmentDeleteConfirm
            attachmentDeleteConfirmView
            attachmentImageOwnerAsAttachmentDeleteConfirm
            attachmentListOwnerAsAttachmentView
            attachmentViewer
            backgroundOpacity
            componentClassName
            componentName
            deleteMessageConfirmView
            followerOwnerAsSubtypeList
            followerSubtypeList
            isCloseable
            manager
            messageActionListOwnerAsDeleteConfirm
            record
            style
        [Model/id]
            Dialog/attachmentCardOwnerAsAttachmentDeleteConfirm
            .{|}
                Dialog/attachmentImageOwnerAsAttachmentDeleteConfirm
            .{|}
                Dialog/attachmentListOwnerAsAttachmentView
            .{|}
                Dialog/followerOwnerAsSubtypeList
            .{|}
                Dialog/messageActionListOwnerAsDeleteConfirm
        [Model/actions]
            Dialog/hasElementInContent
`;
