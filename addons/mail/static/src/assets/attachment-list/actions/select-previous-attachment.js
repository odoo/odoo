/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Select the next attachment.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentList/selectPreviousAttachment
        [Action/params]
            record
                [type]
                    AttachmentList
        [Action/behavior]
            :index
                @record
                .{AttachmentList/attachments}
                .{Collection/findIndex}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            attachment
                        [Function/out]
                            @attachment
                            .{=}
                                @record
                                .{AttachmentList/selectedAttachment}
            :prevIndex
                {if}
                    @index
                    .{=}
                        0
                .{then}
                    @record
                    .{AttachmentList/attachments}
                    .{Collection/length}
                    .{-}
                        1
                .{else}
                    @index
                    .{-}
                        1
            {Record/update}
                [0]
                    @record
                [1]
                    [AttachmentList/selectedAttachment]
                        @record
                        .{AttachmentList/attachments}
                        .{Collection/at}
                            @prevIndex
`;
