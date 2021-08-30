/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            onChange
        [onChange/name]
            onThreadIsLoadingAttachmentsChanged
        [onChange/model]
            Chatter
        [onChange/dependencies]
            Chatter/threadIsLoadingAttachments
        [onChange/behavior]
            {if}
                @record
                .{Chatter/thread}
                .{isFalsy}
                .{|}
                    @record
                    .{Chatter/thread}
                    .{Thread/isLoadingAttachments}
                    .{isFalsy}
            .{then}
                {Chatter/_stopAttachmentsLoading}
                    @record
                {break}
            {if}
                @record
                .{Chatter/isPreparingAttachmentsLoading}
                .{|}
                    @record
                    .{Chatter/isShowingAttachmentsLoading}
            .{then}
                {break}
            {Chatter/_prepareAttachmentsLoading}
                @record
`;
