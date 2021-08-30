/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtcSessions
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            RtcSession
        [Field/inverse]
            RtcSession/channel
        [Field/isCausal]
            true
`;
