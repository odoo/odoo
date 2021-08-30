/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            onChange
        [onChange/name]
            Env/_onChangeFocusedRtcSession
        [onChange/model]
            Env
        [onChange/dependencies]
            Env/focusedRtcSession
        [onChange/behavior]
            {Rtc/filterIncomingVideoTraffic}
                [0]
                    {Env/rtc}
                [1]
                    {Env/focusedRtcSession}
                    .{&}
                        {Env/focusedRtcSession}
                        .{RtcSession/peerToken}
`;
