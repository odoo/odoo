/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            canPostMessage
        [Field/model]
            Composer
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            {if}
                @record
                .{Composer/thread}
                .{&}
                    @record
                    .{Composer/textInputContent}
                    .{isFalsy}
                .{&}
                    @record
                    .{Composer/attachments}
                    .{Collection/length}
                    .{=}
                        0
            .{then}
                false
            .{else}
                @record
                .{Composer/hasUploadingAttachment}
                .{isFalsy}
                .{&}
                    @record
                    .{Composer/isPostingMessage}
                    .{isFalsy}
`;
