/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            iconVideo
        [Element/model]
            AttachmentViewerComponent
        [web.Element/tag]
            i
        [web.Element/role]
            img
        [web.Element/class]
            fa
            fa-video-camera
        [Element/isPresent]
            @record
            .{AttachmentViewerComponent/record}
            .{AttachmentViewer/attachment}
            .{Attachment/isVideo}
        [web.Element/title]
            {Locale/text}
                Video
`;
