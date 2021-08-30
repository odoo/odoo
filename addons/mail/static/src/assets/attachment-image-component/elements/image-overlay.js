/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            imageOverlay
        [Element/model]
            AttachmentImageComponent
        [Element/isPresent]
            @record
            .{AttachmentImageComponent/attachmentImage}
            .{AttachmentImage/attachment}
            .{Attachment/isUploading}
            .{isFalsy}
        [web.Element/class]
            text-right
            p-2
            text-white
            opacity-0
            opacity-100-hover
        [web.Element/style]
            {web.scss/o-position-absolute}
                0
                0
                0
                0
`;
