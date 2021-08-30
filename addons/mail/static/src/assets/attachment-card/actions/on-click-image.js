/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens the attachment viewer when clicking on viewable attachment.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentCard/onClickImage
        [Action/params]
            record
                [type]
                    AttachmentCard
        [Action/behavior]
            {if}
                @record
                .{AttachmentCard/attachment}
                .{Attachment/isViewable}
                .{isFalsy}
            .{then}
                {break}
            {Record/update}
                [0]
                    @record
                    .{AttachmentCard/attachmentList}
                [1]
                    [AttachmentList/attachmentListViewDialog]
                        {Record/insert}
                            [Record/models]
                                Dialog
                    [attachmentListViewDialog/selectedAttachment]
                        @record
                        .{AttachmentCard/attachment}
`;
