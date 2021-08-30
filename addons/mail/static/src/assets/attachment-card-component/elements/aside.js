/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            aside
        [Element/model]
            AttachmentCardComponent
        [Element/isPresent]
            @record
            .{AttachmentCardComponent/attachmentCard}
            .{AttachmentCard/attachmentList}
            .{AttachmentList/composerViewOwner}
            .{isFalsy}
            .{|}
                @record
                .{AttachmentCardComponent/attachment}
                .{Attachment/isEditable}
        [web.Element/class]
            position-relative
            overflow-hidden
            {if}
                @record
                .{AttachmentCardComponent/attachmentCard}
                .{AttachmentCard/attachmentList}
                .{AttachmentList/composerViewOwner}
                .{&}
                    @record
                    .{AttachmentCardComponent/attachment}
                    .{Attachment/isEditable}
            .{then}
                d-flex
                flex-column
        [web.Element/style]
            {if}
                @record
                .{AttachmentCardComponent/attachmentCard}
                .{AttachmentCard/attachmentList}
                .{AttachmentList/composerViewOwner}
                .{&}
                    @record
                    .{AttachmentCardComponent/attachment}
                    .{Attachment/isEditable}
            .{then}
                [web.scss/min-width]
                    30
                    px
            .{else}
                [web.scss/min-width]
                    50
                    px
`;
