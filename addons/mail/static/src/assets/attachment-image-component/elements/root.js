/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            AttachmentImageComponent
        [web.Element/class]
            d-flex
            position-relative
            m-1
            flex-shrink-0
        [Element/onClick]
            {AttachmentImage/onClickImage}
                [0]
                    @record
                    .{AttachmentImageComponent/attachmentImage}
                [1]
                    @ev
        [web.Element/data-mimetype]
            @record
            .{AttachmentImageComponent/attachmentImage}
            .{AttachmentImage/attachment}
            .{Attachment/mimetype}
        [web.Element/style]
            [web.scss/min-width]
                20
                px
            [web.scss/min-height]
                20
                px
            [web.scss/cursor]
                zoom-in
`;
