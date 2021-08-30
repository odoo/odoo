/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Zoom in the image.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentViewerComponent/_zoomIn
        [Action/params]
            record
            scroll
                [default]
                    false
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                    .{AttachmentViewerComponent/record}
                [1]
                    [AttachmentViewer/scale]
                        @record
                        .{AttachmentViewerComponent/record}
                        .{AttachmentViewer/scale}
                        .{+}
                            {if}
                                @scroll
                            .{then}
                                0.1
                            .{else}
                                0.5
            {AttachmentViewerComponent/_updateZoomerStyle}
                @record
`;
