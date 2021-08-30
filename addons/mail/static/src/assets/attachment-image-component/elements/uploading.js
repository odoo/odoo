/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            uploading
        [Element/model]
            AttachmentImageComponent
        [Element/isPresent]
            @record
            .{AttachmentImageComponent/attachmentImage}
            .{AttachmentImage/attachment}
            .{Attachment/isUploading}
        [web.Element/class]
            d-flex
            align-items-center
            justify-content-center
        [web.Element/title]
            {Locale/text}
                Uploading
        [web.Element/style]
            {web.scss/o-position-absolute}
                0
                0
                0
                0
`;
