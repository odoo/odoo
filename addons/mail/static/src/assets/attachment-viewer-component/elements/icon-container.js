/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            iconContainer
        [Element/model]
            AttachmentViewerComponent
        [Record/models]
            AttachmentViewerComponent/headerItem
        [web.Element/isPresent]
            @record
            .{AttachmentViewerComponent/record}
            .{AttachmentViewer/attachment}
            .{Attachment/isViewable}
        [web.Element/style]
            [web.scss/margin-inline-start]
                {scss/map-get}
                    {scss/$spacers}
                    4
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scs/$spacers}
                    2
`;
