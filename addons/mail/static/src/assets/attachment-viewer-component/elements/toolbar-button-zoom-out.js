/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            toolbarButtonZoomOut
        [Element/model]
            AttachmentViewerComponent
        [Record/models]
            AttachmentViewerComponent/toolbarButton
            Hoverable
        [Element/onClick]
            {web.Event/stopPropagation}
                @ev
            {AttachmentViewerComponent/_zoomOut}
                @record
        [web.Element/title]
            {Locale/text}
                Zoom Out (-)
        [web.Element/role]
            button
        [web.Element/style]
            {if}
                @record
                .{AttachmentViewerComponent/record}
                .{AttachmentViewer/scale}
                .{=}
                    @record
                    .{AttachmentViewerComponent/minScale}
            .{then}
                [web.scss/cursor]
                    not-allowed
                [web.scss/filter]
                    {scss/brightness}
                        1.3
            {if}
                @record
                .{AttachmentViewerComponent/record}
                .{AttachmentViewer/scale}
                .{!=}
                    @record
                    .{AttachmentViewerComponent/minScale}
            .{then}
                [web.scss/color]
                    {scss/gray}
                        400
                [web.scss/cursor]
                    pointer
                {if}
                    @field
                    .{web.Element/isHover}
                .{then}
                    [web.scss/background-color]
                        {scss/$black}
                    [web.scss/color]
                        {scss/lighten}
                            {scss/gray}
                                400
                            15%
`;
