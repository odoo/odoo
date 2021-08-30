/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            image
        [Element/model]
            AttachmentImageComponent
        [web.Element/tag]
            img
        [web.Element/class]
            img
            img-fluid
            my-0
            mx-auto
        [web.Element/src]
            @record
            .{AttachmentImageComponent/attachmentImage}
            .{AttachmentImage/imageUrl}
        [web.Element/alt]
            @record
            .{AttachmentImageComponent/attachmentImage}
            .{AttachmentImage/attachment}
            .{Attachment/name}
        [web.Element/style]
            [web.scss/object-fit]
                contain
            [web.scss/max-width]
                {web.scss/min}
                    [0]
                        100%
                    [1]
                        @record
                        .{AttachmentImageComponent/attachmentImage}
                        .{AttachmentImage/width}
                        .{+}
                            px
            [web.scss/min-height]
                {web.scss/min}
                    [0]
                        100%
                    [1]
                        @record
                        .{AttachmentImageComponent/attachmentImage}
                        .{AttachmentImage/height}
                        .{+}
                            px
`;
