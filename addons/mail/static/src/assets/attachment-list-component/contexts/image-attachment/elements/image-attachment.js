/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            imageAttachment
        [Element/model]
            AttachmentListComponent:imageAttachment
        [Field/target]
            AttachmentImageComponent
        [Record/models]
            AttachmentListComponent/attachment
        [AttachmentImageComponent/attachmentImage]
            @record
            .{AttachmentListComponent:imageAttachment/attachmentImage}
`;
