/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentListComponent/imageAttachments
        [Action/params]
            record
        [Action/behavior]
            @record
            .{AttachmentListComponent/attachments}
            .{Collection/filter}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        item
                    [Function/out]
                        @item
                        .{Attachment/isImage}
`;
