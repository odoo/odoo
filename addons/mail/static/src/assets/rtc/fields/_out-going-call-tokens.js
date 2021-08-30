/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Set of peerTokens, used to track which calls are outgoing,
        which is used when attempting to recover a failed peer connection by
        inverting the call direction.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _outGoingCallTokens
        [Field/model]
            Rtc
        [Field/type]
            attr
        [Field/target]
            Set
        [Field/default]
            {Record/insert}
                [Record/models]
                    Set
`;
