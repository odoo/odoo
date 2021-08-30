/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens the attachment viewer when clicking on viewable attachment.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentImage/onClickImage
        [Action/params]
            record
                [type]
                    AttachmentImage
        [Action/behavior]
            {if}
                @record
                .{AttachmentImage/attachment}
                .{Attachment/isViewable}
                .{isFalsy}
            .{then}
                {break}
            {Record/update}
                [0]
                    @record
                    .{AttachmentImage/attachmentList}
                [1]
                    [AttachmentList/attachmentListViewDialog]
                        {Record/insert}
                            [Record/models]
                                Dialog
                    [AttachmentList/selectedAttachment]
                        @record
                        .{AttachmentImage/attachment}
`;
