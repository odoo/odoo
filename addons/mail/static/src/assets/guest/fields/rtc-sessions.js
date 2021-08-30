/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtcSessions
        [Field/model]
            Guest
        [Field/type]
            many
        [Field/target]
            RtcSession
        [Field/inverse]
            RtcSession/guest
`;
