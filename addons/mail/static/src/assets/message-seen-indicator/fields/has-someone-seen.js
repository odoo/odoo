/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasSomeoneSeen
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
                    .{Thread/partnerSeenInfos}
                    .{isFalsy}
            .{then}
                false
            .{else}
                :otherPartnerSeenInfosSeen
                    @record
                    .{MessageSeenIndicator/thread}
                    .{Thread/partnerSeenInfos}
                    .{Collection/filter}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                item
                            [Function/out]
                                @item
                                .{ThreadPartnerSeenInfo/partner}
                                .{!=}
                                    @record
                                    .{MessageSeenIndicator/message}
                                    .{Message/author}
                                .{&}
                                    @item
                                    .{ThreadPartnerSeenInfo/lastSeenMessage}
                                .{&}
                                    @item
                                    .{ThreadPartnerSeenInfo/lastSeenMessage}
                                    .{Message/id}
                                    .{>=}
                                        @record
                                        .{MessageSeenIndicator/message}
                                        .{Message/id}
                @otherPartnerSeenInfosSeen
                .{Collection/length}
                .{>}
                    0
`;
