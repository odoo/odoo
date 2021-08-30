/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            iconImage
        [Element/model]
            AttachmentViewerComponent
        [web.Element/tag]
            i
        [web.Element/role]
            img
        [web.Element/class]
            fa
            fa-picture-o
        [Element/isPresent]
            @record
            .{AttachmentViewerComponent/record}
            .{AttachmentViewer/attachment}
            .{Attachment/isImage}
        [web.Element/title]
            {Locale/text}
                Image
`;
