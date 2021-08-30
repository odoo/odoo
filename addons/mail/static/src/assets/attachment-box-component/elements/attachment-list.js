/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            attachmentList
        [Element/model]
            AttachmentBoxComponent
        [Field/target]
            AttachmentListComponent
        [Element/isPresent]
            @record
            .{AttachmentBoxComponent/attachmentBoxView}
            .{AttachmentBoxView/attachmentList}
        [AttachmentListComponent/attachmentList]
            @record
            .{AttachmentBoxComponent/attachmentBoxView}
            .{AttachmentBoxView/attachmentList}
`;
