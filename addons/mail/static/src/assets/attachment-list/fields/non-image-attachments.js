/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the attachment that are not an image.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            nonImageAttachments
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
                [in]
                    item
                [out]
                    @item
                    .{Attachment/isImage}
                    .{isFalsy}
`;
