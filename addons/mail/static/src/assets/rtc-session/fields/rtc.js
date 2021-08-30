/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        If set, this session is the session of the current user and is in the active RTC call.
        This information is distinct from this.isOwnSession as there can be other
        sessions from other channels with the same partner (sessions opened from different
        tabs or devices).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            Rtc
        [Field/model]
            RtcSession
        [Field/type]
            one
        [Field/target]
            Rtc
        [Field/inverse]
            Rtc/currentRtcSession
`;
