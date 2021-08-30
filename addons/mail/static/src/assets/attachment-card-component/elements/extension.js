/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            extension
        [Element/model]
            AttachmentCardComponent
        [Element/isPresent]
            @record
            .{AttachmentCardComponent/attachmentCard}
            .{AttachmentCard/attachment}
            .{Attachment/extension}
        [web.Element/class]
            text-uppercase
        [web.Element/textContent]
            @record
            .{AttachmentCardComponent/attachmentCard}
            .{AttachmentCard/attachment}
            .{Attachment/extension}
        [web.Element/style]
            [web.scss/font-size]
                80%
            [web.scss/font-weight]
                400
`;
