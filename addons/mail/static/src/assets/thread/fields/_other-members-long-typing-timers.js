/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Registry of timers of partners currently typing in the thread,
        excluding current partner. This is useful in order to
        automatically unregister typing members when not receive any
        typing notification after a long time. Timers are internally
        indexed by partner records as key. The current partner is
        ignored in this registry of timers.

        @see Thread/registerOtherMemberTypingMember
        @see Thread/unregisterOtherMemberTypingMember
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _otherMembersLongTypingTimers
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Timer
        [Field/isCausal]
            true
`;