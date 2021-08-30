/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The mail.channel of the session, rtc sessions are part and managed by
        mail.channel
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            channel
        [Field/model]
            RtcSession
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/inverse]
            Thread/rtcSessions
`;
