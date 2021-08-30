/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Timer of current partner that was currently typing something, but
        there is no change on the input for 5 seconds. This is used
        in order to automatically notify other members that current
        partner has stopped typing something, due to making no changes
        on the composer for some time.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _currentPartnerInactiveTypingTimer
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
                    5000
                [Timer/timeout]
                    {Record/doAsync}
                        [0]
                            @record
                        [1]
                            {if}
                                {Env/currentPartner}
                            .{then}
                                {Thread/_onCurrentPartnerInactiveTypingTimeout}
                                    @record
`;
