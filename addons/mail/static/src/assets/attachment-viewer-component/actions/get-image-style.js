/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Compute the style of the image (scale + rotation).
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentViewerComponent/getImageStyle
        [Action/params]
            record
        [Action/behavior]
            :style
                [web.scss/transform]
                    {web.scss/scale3d}
                        []
                            @record
                            .{AttachmentViewerComponent/record}
                            .{AttachmentViewer/scale}
                        []
                            @record
                            .{AttachmentViewerComponent/record}
                            .{AttachmentViewer/scale}
                        []
                            1
                    {web.scss/rotate}
                        []
                            @record
                            .{AttachmentViewerComponent/record}
                            .{AttachmentViewer/angle}
                        []
                            deg
            {if}
                @record
                .{AttachmentViewerComponent/record}
                .{AttachmentViewer/angle}
                .{%}
                    180
                .{!=}
                    0
            .{then}
                {Record/update}
                    [0]
                        @style
                    [1]
                        [web.scss/max-height]
                            {Device/globalWindowInnerWidth}
                            px
                        [web.scss/max-width] 
                            {Device/globalWindowInnerHeight}
                            px
            .{else}
                    {Record/update}
                        [0]
                            @style
                        [1]
                            [web.scss/max-height]
                                100%
                            [web.scss/max-width]
                                100%
            @style
`;
