/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentImageOwnerAsAttachmentDeleteConfirm
        [Field/model]
            Dialog
        [Field/type]
            one
        [Field/target]
            AttachmentImage
        [Field/isReadonly]
            true
        [Field/inverse]
            AttachmentImage/attachmentDeleteConfirmDialog
`;
