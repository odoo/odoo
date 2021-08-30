/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageSeenIndicator/recomputeSeenValues
        [Action/params]
            channel
                [type]
                    Thread
                [description]
                    the concerned thread
        [Action/behavior]
            :indicatorFindFunction
                {if}
                    @channel
                .{then}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            item
                        [Function/out]
                            @item
                            .{MessageSeenIndicator/thread}
                            .{=}
                                @channel
                .{else}
                    undefined
            :indicators
                {Record/all}
                    [Record/models]
                        MessageSeenIndicator
                    @indicatorFindFunction
            {foreach}
                @indicators
            .{as}
                indicator
            .{do}
                {Record/update}
                    [0]
                        @indicator
                    [1]
                        [MessageSeenIndicator/hasEveryoneSeen]
                            {MessageSeenIndicator/_computeHasEveryoneSeen}
                                @indicator
                        [MessageSeenIndicator/hasSomeoneFetched]
                            {MessageSeenIndicator/_computeHasSomeoneFetched}
                                @indicator
                        [MessageSeenIndicator/hasSomeoneSeen]
                            {MessageSeenIndicator/_computeHasSomeoneSeen}
                                @indicator
                        [MessageSeenIndicator/isMessagePreviousToLastCurrentPartnerMessageSeenByEveryone]
                            {MessageSeenIndicator/_computeIsMessagePreviousToLastCurrentPartnerMessageSeenByEveryone}
                                @indicator
                        [MessageSeenIndicator/partnersThatHaveFetched]
                            {MessageSeenIndicator/_computePartnersThatHaveFetched}
                                @indicator
                        [MessageSeenIndicator/partnersThatHaveSeen]
                            {MessageSeenIndicator/_computePartnersThatHaveSeen}
                                @indicator
`;
