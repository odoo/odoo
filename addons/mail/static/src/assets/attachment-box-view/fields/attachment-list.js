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
            AttachmentBoxView
        [Field/type]
            one
        [Field/target]
            AttachmentList
        [Field/inverse]
            AttachmentList/attachmentBoxViewOwner
        [Field/isCausal]
            true
        [Field/readonly]
            true
        [Field/compute]
            {if}
                @record
                .{AttachmentBoxView/chatter}
                .{Chatter/thread}
                .{&}
                    @record
                    .{AttachmentBoxView/chatter}
                    .{Chatter/thread}
                    .{Thread/allAttachments}
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
