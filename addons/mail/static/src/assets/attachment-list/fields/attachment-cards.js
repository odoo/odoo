/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the attachment cards that are displaying this nonImageAttachments.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentCards
        [Field/model]
            AttachmentList
        [Field/type]
            many
        [Field/target]
            AttachmentCard
        [Field/isCausal]
            true
        [Field/inverse]
            AttachmentCard/attachmentList
        [Field/compute]
            @record
            .{AttachmentList/nonImageAttachments}
            .{Collection/map}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        item
                    [Function/out]
                        {Record/insert}
                            [Record/models]
                                AttachmentCard
                            [AttachmentCard/attachment]
                                @item
`;
