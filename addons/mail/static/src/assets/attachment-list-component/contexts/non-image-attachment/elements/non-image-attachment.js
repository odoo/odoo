/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            nonImageAttachment
        [Element/model]
            AttachmentListComponent:nonImageAttachment
        [Field/target]
            AttachmentCardComponent
        [Record/models]
            AttachmentListComponent/attachment
        [AttachmentCardComponent/attachmentCard]
            @record
            .{AttachmentListComponent:nonImageAttachment/attachmentCard}
`;
