/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_setMuteState
        [Action/params]
            isSelfMuted
                [type]
                    Boolean
        [Action/behavior]
            {RtcSession/updateAndBroadcast}
                [0]
                    {Rtc/currentRtcSession}
                [1]
                    [isSelfMuted]
                        @isSelfMuted
            {Rtc/_updateLocalAudioTrackEnabledState}
`;
