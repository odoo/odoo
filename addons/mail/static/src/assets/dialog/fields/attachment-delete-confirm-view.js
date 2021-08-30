/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentDeleteConfirmView
        [Field/model]
            Dialog
        [Field/type]
            one
        [Field/target]
            AttachmentDeleteConfirmView
        [Field/isCausal]
            true
        [Field/inverse]
            AttachmentDeleteConfirmView/dialogOwner
        [Field/compute]
            {if}
                @record
                .{Dialog/attachmentCardOwnerAsAttachmentDeleteConfirm}
            .{then}
                {Record/insert}
                    [Record/models]
                        AttachmentDeleteConfirmView
            .{elif}
                @record
                .{Dialog/attachmentImageOwnerAsAttachmentDeleteConfirm}
            .{then}
                {Record/insert}
                    [Record/models]
                        AttachmentDeleteConfirmView
            .{else}
                {Record/empty}
`;
