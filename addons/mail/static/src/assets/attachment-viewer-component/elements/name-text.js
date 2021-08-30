/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            nameText
        [Element/model]
            AttachmentViewerComponent
        [web.Element/tag]
            span
        [web.Element/class]
            text-truncate
        [web.Element/textContent]
            @record
            .{AttachmentViewerComponent/record}
            .{AttachmentViewer/attachment}
            .{Attachment/displayName}
`;
