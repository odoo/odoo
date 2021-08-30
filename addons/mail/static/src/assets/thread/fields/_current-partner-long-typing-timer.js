/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Timer of current partner that is typing a very long text. When
        the other members do not receive any typing notification for a
        long time, they must assume that the related partner is no longer
        typing something (e.g. they have closed the browser tab).
        This is a timer to let other members know that current partner
        is still typing something, so that they should not assume he/she
        has stopped typing something.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _currentPartnerLongTypingTimer
        [Field/model]
            Thread
        [Field/type]
            one
        [Field/target]
            Timer
        [Field/isCausal]
            true
        [Field/default]
            {Record/insert}
                [Record/models]
                    Timer
                [Timer/duration]
                    50000
                [Timer/timeout]
                    {Record/doAsync}
                        @record
                            {Thread/_onCurrentPartnerLongTypingTimeout}
                                @record
`;
