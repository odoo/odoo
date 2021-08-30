/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Stop dragging interaction of the user.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentViewerComponent/_stopDragging
        [Action/params]
            record
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                    .{AttachmentViewerComponent/attachmentViewer}
                [1]
                    [AttachmentViewer/isDragging]
                        false
            {Record/update}
                [0]
                    @record
                [1]
                    [AttachmentViewerComponent/translateDx]
                        0
                    [AttachmentViewerComponent/translateDy]
                        0
                    [AttachmentViewerComponent/translateX]
                        {Field/add}
                            @record
                            .{AttachmentViewerComponent/translateDx}
                    [AttachmentViewerComponent/translateY]
                        {Field/add}
                            @record
                            .{AttachmentViewerComponent/translateDy}
            {AttachmentViewerComponent/_updateZoomerStyle}
                @record
`;
