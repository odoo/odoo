/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the attachment images that are displaying this imageAttachments.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentListViewDialog
        [Field/model]
            AttachmentList
        [Field/type]
            one
        [Field/target]
            Dialog
        [Field/isCausal]
            true
        [FIeld/inverse]
            Dialog/attachmentListOwnerAsAttachmentView
`;
