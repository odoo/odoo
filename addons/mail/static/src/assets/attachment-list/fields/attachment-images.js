/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the attachment images that are displaying this imageAttachments.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentImages
        [Field/model]
            AttachmentList
        [Field/type]
            many
        [Field/target]
            AttachmentImage
        [Field/isCausal]
            true
        [FIeld/inverse]
            AttachmentImage/attachmentList
        [Field/compute]
            @record
            .{AttachmentList/imageAttachments}
            .{Collection/map}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        item
                    [Function/out]
                        {Record/insert}
                            [Record/models]
                                AttachmentImage
                            [AttachmentImage/attachment]
                                @item
`;
