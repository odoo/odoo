/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentDeleteConfirmDialog
        [Field/model]
            AttachmentCard
        [Field/type]
            one
        [Field/target]
            Dialog
        [Field/isCausal]
            true
        [Field/inverse]
            Dialog/attachmentCardOwnerAsAttachmentDeleteConfirm
`;
