/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            viewVideoSource
        [Element/model]
            AttachmentViewerComponent
        [web.Element/tag]
            source
        [web.Element/data-type]
            @record
            .{AttachmentViewerComponent/record}
            .{AttachmentViewer/attachment}
            .{Attachment/mimetype}
        [web.Element/src]
            @record
            .{AttachmentViewerComponent/record}
            .{AttachmentViewer/attachment}
            .{Attachment/defaultSource}
`;
