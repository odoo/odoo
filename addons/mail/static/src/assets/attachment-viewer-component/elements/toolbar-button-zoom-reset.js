/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            toolbarButtonZoomReset
        [Element/model]
            AttachmentViewerComponent
        [Record/models]
            AttachmentViewerComponent/toolbarButton
            Hoverable
        [Element/onClick]
            {web.Event/stopPropagation}
                @ev
            {AttachmentViewerComponent/_zoomReset}
                @record
        [web.Element/role]
            button
        [web.Element/title]
            {Locale/text}
                Reset Zoom (0)
        [web.Element/style]
            {if}
                @record
                .{AttachmentViewerComponent/record}
                .{AttachmentViewer/scale}
                .{=}
                    1
            .{then}
                [web.scss/cursor]
                    not-allowed
                [web.scss/filter]
                    {web.scss/brightness}
                        1.3
            {if}
                @record
                .{AttachmentViewerComponent/record}
                .{AttachmentViewer/scale}
                .{!=}
                    1
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
