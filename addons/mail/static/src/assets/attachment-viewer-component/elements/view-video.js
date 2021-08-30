/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            viewVideo
        [Element/model]
            AttachmentViewerComponent
        [web.Element/tag]
            video
        [Record/models]
            AttachmentViewerComponent/view
        [web.Element/controls]
            controls
        [Element/isPresent]
            @record
            .{AttachmentViewerComponent/record}
            .{AttachmentViewer/attachment}
            .{Attachment/isVideo}
        [Element/onClick]
            {Dev/comment}
                Stop propagation to prevent closing the dialog.
            {web.Event/stopPropagation}
                @ev
        [web.Element/style]
            [web.scss/width]
                75%
            [web.scss/height]
                75%
            {if}
                {Device/isMobile}
            .{then}
                [web.scss/width]
                    {scss/map-get}
                        {scss/$sizes}
                        100
                [web.scss/height]
                    {scss/map-get}
                        {scss/$sizes}
                        100
`;
