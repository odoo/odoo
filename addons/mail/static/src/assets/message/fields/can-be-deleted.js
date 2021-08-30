/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Whether this message can be deleted.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            canBeDeleted
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {if}
                {Session/is_admin}
                .{isFalsy}
                .{&}
                    @record
                    .{Message/isCurrentUserOrGuestAuthor}
                    .{isFalsy}
            .{then}
                false
            .{elif}
                @record
                .{Message/originThread}
                .{isFalsy}
            .{then}
                false
            .{elif}
                @record
                .{Message/trackingValues}
                .{Collection/length}
                .{>}
                    0
            .{then}
                false
            .{elif}
                @record
                .{Message/type}
                .{!=}
                    comment
            .{then}
                false
            .{elif}
                @record
                .{Message/originThread}
                .{Thread/model}
                .{=}
                    mail.channel
            .{then}
                true
            .{else}
                @record
                .{Message/isNote}
`;
