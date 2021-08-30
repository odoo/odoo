/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Zoom out the image.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentViewerComponent/_zoomOut
        [Action/params]
            record
            scroll
                [default]
                    false
        [Action/behavior]
            {if}
                @record
                .{AttachmentViewerComponent/record}
                .{AttachmentViewer/scale}
                .{=}
                    @record
                    .{AttachmentViewerComponent/minScale}
            .{then}
                {break}
            :unflooredAdaptedScale
                @record
                .{AttachmentViewerComponent/record}
                .{AttachmentViewer/scale}
                .{-}
                    {if}
                        @scroll
                    .{then}
                        0.1
                    .{else}
                        0.5
            {Record/update}
                [0]
                    @record
                    .{AttachmentViewerComponent/record}
                [1]
                    [AttachmentViewer/scale]
                        {Math/max}
                            @record
                            .{AttachmentViewerComponent/minScale}
                            @unflooredAdaptedScale
            {AttachmentViewerComponent/_updateZoomerStyle}
                @record
`;
