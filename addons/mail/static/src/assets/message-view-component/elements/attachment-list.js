/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            attachmentList
        [Element/model]
            MessageViewComponent
        [Field/target]
            AttachmentListComponent
        [Element/isPresent]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/attachmentList}
        [AttachmentListComponent/attachmentList]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/attachmentList}
`;
