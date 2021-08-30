/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentListOwnerAsAttachmentView
        [Field/model]
            Dialog
        [Field/type]
            one
        [Field/target]
            AttachmentList
        [Field/inverse]
            AttachmentList/attachmentListViewDialog
        [Field/isReadonly]
            true
`;
