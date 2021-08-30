/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentCardOwnerAsAttachmentDeleteConfirm
        [Field/model]
            Dialog
        [Field/type]
            one
        [Field/target]
            AttachmentCard
        [Field/isReadonly]
            true
        [Field/inverse]
            AttachmentCard/attachmentDeleteConfirmDialog
`;
