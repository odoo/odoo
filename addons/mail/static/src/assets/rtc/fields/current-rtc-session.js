/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        String, peerToken of the current session used to identify him during the peer-to-peer transactions.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            currentRtcSession
        [Field/model]
            Rtc
        [Field/type]
            one
        [Field/target]
            RtcSession
        [Field/inverse]
            RtcSession/rtc
`;
