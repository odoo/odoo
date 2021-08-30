/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the attachment list that will be used to display the attachments.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentList
        [Field/model]
            ComposerView
        [Field/type]
            one
        [Field/target]
            AttachmentList
        [Field/isCausal]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            AttachmentList/composerViewOwner
        [Field/compute]
            {if}
                @record
                .{ComposerView/composer}
                .{&}
                    @record
                    .{ComposerView/composer}
                    .{Composer/attachments}
                    .{Collection/length}
                    .{>}
                        0
            .{then}
                {Record/insert}
                    [Record/models]
                        AttachmentList
            .{else}
                {Record/empty}
`;