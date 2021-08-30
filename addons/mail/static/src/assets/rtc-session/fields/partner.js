/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        If set, the partner who owns this rtc session,
        there can be multiple rtc sessions per partner if the partner
        has open sessions in multiple channels, but only one session per
        channel is allowed.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            partner
        [Field/model]
            RtcSession
        [Field/type]
            one
        [Field/target]
            Partner
        [Field/inverse]
            Partner/rtcSessions
`;
