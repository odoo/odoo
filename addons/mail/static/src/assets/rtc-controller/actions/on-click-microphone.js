/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcController/onClickMicrophone
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    RtcController
        [Action/behavior]
            {if}
                {Rtc/currentRtcSession}
                .{RtcSession/isMute}
            .{then}
                {if}
                    {Rtc/currentRtcSession}
                    .{RtcSession/isSelfMuted}
                .{then}
                    {Rtc/unmute}
                {if}
                    {Rtc/currentRtcSession}
                    .{RtcSession/isDeaf}
                .{then}
                    {Rtc/undeafen}
            .{else}
                {Rtc/mute}
`;
