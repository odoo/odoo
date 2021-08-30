/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Reset the zoom scale of the image.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentViewerComponent/_zoomReset
        [Action/params]
            record
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                    .{AttachmentViewerComponent/record}
                [1]
                    [AttachmentViewer/scale]
                        1
            {AttachmentViewerComponent/_updateZoomerStyle}
                @record
`;
