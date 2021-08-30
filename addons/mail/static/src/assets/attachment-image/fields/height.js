/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the max height of this attachment image in px.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            height
        [Field/model]
            AttachmentImage
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/isRequired]
            true
        [Field/compute]
            {if}
                @record
                .{AttachmentImage/attachmentList}
                .{isFalsy}
            .{then}
                {Record/empty}
            .{elif}
                @record
                .{AttachmentImage/attachmentList}
                .{AttachmentList/composerViewOwner}
            .{then}
                50
            .{elif}
                @record
                .{AttachmentImage/attachmentList}
                .{AttachmentList/attachmentBoxViewOwner}
            .{then}
                160
            .{elif}
                @record
                .{AttachmentImage/attachmentList}
                .{AttachmentList/messageViewOwner}
            .{then}
                300
`;
