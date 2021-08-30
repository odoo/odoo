/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasSomeoneFetched
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
                @see MessageSeenIndicator/computeFetchedValues
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
                :otherPartnerSeenInfosFetched
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
                                    .{ThreadPartnerSeenInfo/lastFetchedMessage}
                                .{&}
                                    @item
                                    .{ThreadPartnerSeenInfo/lastFetchedMessage}
                                    .{Message/id}
                                    .{>=}
                                        @record
                                        .{MessageSeenIndicator/message}
                                        .{message/id}
                @otherPartnerSeenInfosFetched
                .{Collection/length}
                .{>}
                    0
`;
