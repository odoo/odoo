/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            partnersThatHaveFetched
        [Field/model]
            MessageSeenIndicator
        [Field/type]
            many
        [Field/target]
            Partner
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
                {Record/empty}
            .{else}
                :otherPartnersThatHaveFetched
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
                                .{&}
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
                                        .{Message/id}
                    .{Collection/map}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                item
                            [Function/out]
                                @item
                                .{ThreadPartnerSeenInfo/partner}
                {if}
                    @otherPartnersThatHaveFetched
                    .{Collection/length}
                    .{=}
                        0
                .{then}
                    {Record/empty}
                .{else}
                    @otherPartnersThatHaveFetched
`;
