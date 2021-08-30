/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            filename
        [Element/model]
            AttachmentCardComponent
        [Element/isPresent]
            @record
            .{AttachmentCardComponent/attachmentCard}
            .{AttachmentCard/attachment}
            .{Attachment/displayName}
        [web.Element/class]
            overflow-hidden
            text-nowrap
        [web.Element/textContent]
            @record
            .{AttachmentCardComponent/attachmentCard}
            .{AttachmentCard/attachment}
            .{Attachment/displayName}
        [web.Element/style]
            [web.scss/text-overflow]
                ellipsis
`;
