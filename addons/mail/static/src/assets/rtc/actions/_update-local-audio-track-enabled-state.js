/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Sets the enabled property of the local audio track and notifies
        peers of the new state.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_updateLocalAudioTrackEnabledState
        [Action/params]
            record
                [type]
                    Rtc
        [Action/behavior]
            {if}
                @record
                .{Rtc/audioTrack}
                .{isFalsy}
            .{then}
                {break}
            {Record/update}
                [0]
                    @record
                    .{Rtc/audioTrack}
                [1]
                    [Track/enabled]
                        @record
                        .{Rtc/currentRtcSession}
                        .{RtcSession/isMute}
                        .{isFalsy}
                        .{&}
                            @record
                            .{Rtc/currentRtcSession}
                            .{RtcSession/isTalking}
            {Rtc/_notifyPeers}
                [0]
                    @record
                [1]
                    @record
                    .{Rtc/_peerConnections}
                    .{Dict/keys}
                [2]
                    [event]
                        trackChange
                    [type]
                        peerToPeer
                    [payload]
                        [type]
                            audio
                        [state]
                            [isTalking]
                                {Rtc/audioTrack}
                                .{AudioTrack/enabled}
                            [isSelfMuted]
                                @record
                                .{Rtc/currentRtcSession}
                                .{RtcSession/isSelfMuted}
                            [isDeaf]
                                @record
                                .{Rtc/currentRtcSession}
                                .{RtcSession/isDeaf}
`;
