/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            image
        [Element/model]
            AttachmentCardComponent
        [web.Element/class]
            {Dev/comment}
                o_image from mimetype.scss
            o_image
        [web.Element/data-mimetype]
            @record
            .{AttachmentCardComponent/attachmentCard}
            .{AttachmentCard/attachment}
            .{Attachment/mimetype}
        [Element/onClick]
            {AttachmentCard/onClickImage}
                [0]
                    @record
                    .{AttachmentCardComponent/attachmentCard}
                [1]
                    @ev
        [web.Element/style]
            [web.scss/flex-shrink]
                0
            [web.scss/margin]
                3
                px
            {if}
                @record
                .{AttachmentCardComponent/attachmentCard}
                .{AttachmentCard/attachment}
                .{Attachment/isViewable}
            .{then}
                [web.scss/cursor]
                    zoom-in
`;
