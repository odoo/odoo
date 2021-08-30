/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_handleTrackChange
        [Action/params]
            rtcSession
                [type]
                    RtcSession
            type
                [type]
                    String
                [description]
                    'audio' or 'video'
            state
                [type]
                    Object
            record
                [type]
                    Rtc
        [Action/behavior]
            {if}
                @type
                .{=}
                    audio
            .{then}
                {if}
                    @rtcSession
                    .{RtcSession/audioStream}
                    .{isFalsy}
                .{then}
                    {break}
                {Record/update}
                    [0]
                        @rtcSession
                    [1]
                        [RtcSession/isSelfMuted]
                            @state
                            .{Dict/get}
                                isSelfMuted
                        [RtcSession/isTalking]
                            @state
                            .{Dict/get}
                                isTalking
                        [RtcSession/isDeaf]
                            @state
                            .{Dict/get}
                                isDeaf
            {if}
                @type
                .{=}
                    video
                .{&}
                    @state
                    .{Dict/get}
                        isSendingVideo
                    .{=}
                        false
            .{then}
                {Dev/comment}
                    Since WebRTC "unified plan", the local track is tied to the
                    remote transceiver.sender and not the remote track. Therefore
                    when the remote track is 'ended' the local track is not 'ended'
                    but only 'muted'. This is why we do not stop the local track
                    until the peer is completely removed.
                {Record/update}
                    [0]
                        @rtcSession
                    [1]
                        [RtcSession/videoStream]
                            {Record/empty}
                {RtcSession/removeVideo}
                    [0]
                        @rtcSession
                    [1]
                        [stopTracks]
                            false
`;
