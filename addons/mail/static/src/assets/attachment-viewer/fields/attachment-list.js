/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentList
        [Field/model]
            AttachmentViewer
        [Field/type]
            one
        [Field/target]
            AttachmentList
        [Field/isRequired]
            true
        [Field/related]
            AttachmentViewer/dialogOwner
            Dialog/attachmentListOwnerAsAttachmentView
`;
