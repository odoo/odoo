/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            toolbar
        [Element/model]
            AttachmentViewerComponent
        [Element/isPresent]
            @record
            .{AttachmentViewerComponent/record}
            .{AttachmentViewer/attachment}
            .{Attachment/isImage}
        [web.Element/role]
            toolbar
        [web.Element/style]
            [web.scss/position]
                absolute
            [web.scss/bottom]
                45
                px
            [web.scss/transform]
                {web.scss/translateY}
                    100%
            [web.scss/display]
                flex
            [web.scss/cursor]
                pointer
`;
