/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            iconText
        [Element/model]
            AttachmentViewerComponent
        [web.Element/tag]
            i
        [web.Element/role]
            img
        [web.Element/class]
            fa
            fa-file-text
        [Element/isPresent]
            @record
            .{AttachmentViewerComponent/record}
            .{AttachmentViewer/attachment}
            .{Attachment/isText}
        [web.Element/title]
            {Locale/text}
                Text file
`;
