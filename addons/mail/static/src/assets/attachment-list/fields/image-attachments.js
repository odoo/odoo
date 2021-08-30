/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the attachment that are an image.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            imageAttachments
        [Field/model]
            AttachmentList
        [Field/type]
            many
        [Field/target]
            Attachment
        [Field/compute]
            @record
            .{AttachmentList/attachments}
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
