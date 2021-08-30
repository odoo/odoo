/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            AttachmentCardComponent
        [web.Element/class]
            d-flex
        [web.Element/title]
            {if}
                @record
                .{AttachmentCardComponent/attachmentCard}
                .{AttachmentCard/attachment}
                .{Attachment/displayName}
            .{then}
                @record
                .{AttachmentCardComponent/attachmentCard}
                .{AttachmentCard/attachment}
                .{Attachment/displayName}
        [web.Element/style]
            [web.scss/background-color]
                {scss/gray}
                    300
            [web.scss/border-radius]
                5
                px
`;
