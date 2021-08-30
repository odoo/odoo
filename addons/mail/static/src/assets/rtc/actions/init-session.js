/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/initSession
        [Action/params]
            currentSessionId
                [type]
                    Integer
                [description]
                    the Id of the 'mail.rtc_session'
                    of the current partner for the current call
            iceServers
                [type]
                    Collection<Object>
            startWithAudio
                [type]
                    Boolean
            startWithVideo
                [type]
                    Boolean
            videoType
                [type]
                    String
                [description]
                    'user-video' or 'display'
            record
                [type]
                    Rtc
        [Action/behavior]
            {Dev/comment}
                Initializing a new session implies closing the current session.
            {Rtc/reset}
                @record
            [Record/update}
                [0]
                    @record
                [1]
                    [Rtc/currentRtcSession]
                        {Record/insert}
                            [Record/models]
                                RtcSession
                            [RtcSession/id]
                                @currentSessionId
                    [Rtc/iceServers]
                        @iceServers
                        .{|}
                            @record
                            .{Rtc/iceServers}
            {Rtc/_callSessions}
                @record
            {Rtc/updateLocalAudioTrack}
                [0]
                    @record
                [1]
                    @startWithAudio
            {if}
                @startWithVideo
            .{then}
                {Rtc/_toggleVideoBroadcast}
                    [0]
                        @record
                    [1]
                        [type]
                            @videoType
`;
