/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The session that invited the current user, it is only set when the
        invitation is still pending.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtcInvitingSession
        [Field/model]
            Thread
        [Field/type]
            one
        [Field/target]
            RtcSession
        [Field/inverse]
            RtcSession/calledChannels
`;
