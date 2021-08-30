/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Rotate the image by 90 degrees to the right.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentViewerComponent/_rotate
        [Action/params]
            record
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                    .{AttachmentViewerComponent/record}
                [1]
                    [AttachmentViewer/angle]
                        @record
                        .{AttachmentViewerComponent/record}
                        .{AttachmentViewer/angle}
                        .{+}
                            90
`;
