/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            nonImageAttachmentForeach
        [Element/model]
            AttachmentListComponent
        [Record/models]
            Foreach
        [Field/target]
            AttachmentListComponent:nonImageAttachment
        [Foreach/collection]
            {AttachmentListComponent/attachmentCards}
                @record
        [Foreach/as]
            attachmentCard
        [AttachmentListComponent:nonImageAttachment/attachmentCard]
            @field
            .{Foreach/get}
                attachmentCard
        [Element/key]
            @field
            .{Foreach/get}
                attachmentCard
            .{Record/id}
`;
