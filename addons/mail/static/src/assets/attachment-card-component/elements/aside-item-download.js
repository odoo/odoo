/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            asideItemDownload
        [Element/model]
            AttachmentCardComponent
        [Record/models]
            AttachmentCardComponent/asideItem
        [Element/isPresent]
            @record
            .{AttachmentCardComponent/attachmentCard}
            .{AttachmentCard/attachmentList}
            .{AttachmentList/composerViewOwner}
            .{isFalsy}
            .{&}
                @record
                .{AttachmentCardComponent/attachmentCard}
                .{AttachmentCard/attachment}
                .{Attachment/isUploading}
                .{isFalsy}
        [web.Element/title]
            {Locale/text}
                Download
        [Element/onClick]
            {Attachment/onClickDownload}
                [0]
                    @record
                    .{AttachmentCardComponent/attachmentCard}
                    .{AttachmentCard/attachment}
                [1]
                    @ev
        [web.Element/style]
            [web.scss/cursor]
                pointer
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/background-color]
                    {scss/gray}
                        400
`;
