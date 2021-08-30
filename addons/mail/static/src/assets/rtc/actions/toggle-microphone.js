/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Mutes and unmutes the microphone, will not unmute if deaf.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/toggleMicrophone
        [Action/behavior]
            {if}
                {Rtc/currentRtcSession}
                .{RtcSession/isMute}
            .{then}
                {Rtc/unmute}
            .{else}
                {Rtc/mute}
`;
