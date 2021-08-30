/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            zoomer
        [Element/model]
            AttachmentViewerComponent
        [Element/isPresent]
            @record
            .{AttachmentViewerComponent/record}
            .{AttachmentViewer/attachment}
            .{Attachment/isImage}
        [web.Element/style]
            [web.scss/position]
                absolute
            [web.scss/padding]
                45px
                0
            [web.scss/height]
                100%
            [web.scss/width]
                100%
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/justify-content]
                center
`;
