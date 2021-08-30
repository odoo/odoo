/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isMessagePreviousToLastCurrentPartnerMessageSeenByEveryone
        [Field/model]
            MessageSeenIndicator
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            {Dev/comment}
                Manually called as not always called when necessary
                @see MessageSeenIndicator/computeSeenValues
            {if}
                @record
                .{MessageSeenIndicator/message}
                .{isFalsy}
                .{|}
                    @record
                    .{MessageSeenIndicator/thread}
                    .{isFalsy}
                .{|}
                    @record
                    .{MessageSeenIndicator/thread}
                    .{Thread/lastCurrentPartnerMessageSeenByEveryone}
                    .{isFalsy}
            .{then}
                false
            .{else}
                @record
                .{MessageSeenIndicator/message}
                .{Message/id}
                .{<}
                    @record
                    .{MessageSeenIndicator/thread}
                    .{Thread/lastCurrentPartnerMessageSeenByEveryone}
                    .{Partner/id}
`;
