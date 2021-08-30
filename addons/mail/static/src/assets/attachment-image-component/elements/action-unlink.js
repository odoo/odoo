/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            actionUnlink
        [Element/model]
            AttachmentImageComponent
        [Record/models]
            AttachmentImageComponent/action
        [web.Element/class]
            btn
            btn-sm
            btn-dark
            rounded
            opacity-75
            opacity-100-hover
        [web.Element/title]
            {Locale/text}
                Remove
        [Element/isPresent]
            @record
            .{AttachmentImageComponent/attachmentImage}
            .{AttachmentImage/attachment}
            .{Attachment/isEditable}
        [Element/onClick]
            {AttachmentImage/onClickUnlink}
                [0]
                    @record
                    .{AttachmentImageComponent/attachmentImage}
                [1]
                    @ev
`;
