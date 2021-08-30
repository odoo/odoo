/** @odoo-module**/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the current image is rendered for the 1st time, and if
        that's the case, display a spinner until loaded.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentViewerComponent/_handleImageLoad
        [Action/params]
            record
        [Action/behavior]
            {if}
                @record
                .{AttachmentViewerComponent/record}
                .{isFalsy}
                .{|}
                    @record
                    .{AttachmentViewerComponent/record}
                    .{AttachmentViewer/attachment}
                    .{isFalsy}
            .{then}
                {break}
            {if}
                @record
                .{AttachmentViewerComponent/record}
                .{AttachmentViewer/attachment}
                .{Attachment/isImage}
                .{&}
                    @record
                    .{AttachmentViewerComponent/viewImage}
                    .{isFalsy}
                    .{|}
                        @record
                        .{AttachmentViewerComponent/viewImage}
                        .{web.Element/isComplete}
                        .{isFalsy}
            .{then}
                {Record/update}
                    [0]
                        @record
                        .{AttachmentViewerComponent/record}
                    [1]
                        [AttachmentViewer/isImageLoading]
                            true
`;
