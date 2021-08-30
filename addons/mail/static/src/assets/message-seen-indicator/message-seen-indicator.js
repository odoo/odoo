/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MessageSeenIndicator
        [Model/fields]
            hasEveryoneFetched
            hasEveryoneSeen
            hasSomeoneFetched
            hasSomeoneSeen
            id
            isMessagePreviousToLastCurrentPartnerMessageSeenByEveryone
            message
            partnersThatHaveFetched
            partnersThatHaveSeen
            thread
            title
        [Model/id]
            MessageSeenIndicator/thread
            .{&}
                MessageSeenIndicator/message
        [Model/actions]
            MessageSeenIndicator/recomputeFetchedValues
            MessageSeenIndicator/recomputeSeenValues
`;
