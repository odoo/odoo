/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentListComponent/nonImageAttachments
        [Action/params]
            record
        [Action/behavior]
            @record
            .{AttachmentListComponent/attachments}
            .{Collection/filter}
                [in]
                    item
                [out]
                    @item
                    .{Attachment/isImage}
                    .{isFalsy}
`;
