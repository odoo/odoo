/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Updates the "isTalking" state of the current user and sets the
        enabled state of its audio track accordingly.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_setSoundBroadcast
        [Action/params]
            isTalking
                [type]
                    Boolean
            record
                [type]
                    Rtc
        [Action/behavior]
            {if}
                @record
                .{Rtc/currentRtcSession}
                .{isFalsy}
            .{then}
                {break}
            {if}
                @isTalking
                .{=}
                    @record
                    .{Rtc/currentRtcSession}
                    .{RtcSession/isTalking}
            .{then}
                {break}
            {Record/update}
                [0]
                    @record
                    .{Rtc/currentRtcSession}
                [1]
                    [RtcSession/isTalking]
                        @isTalking
            {if}
                @record
                .{Rtc/currentRtcSession}
                .{RtcSession/isMute}
                .{isFalsy}
            .{then}
                {Rtc/_updateLocalAudioTrackEnabledState}
                    @record
`;
