/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_callSessions
        [Action/params]
            record
                [type]
                    Rtc
        [Action/behavior]
            {if}
                @record
                .{Rtc/channel}
                .{Thread/rtcSessions}
                .{isFalsy}
            .{then}
                {break}
            {foreach}
                @record
                .{Rtc/channel}
                .{Thread/rtcSessions}
            .{as}
                session
            .{do}
                {if}
                    {Dict/hasKey}
                        [0]
                            @record
                            .{Rtc/_peerConnections}
                        [1]
                            @session
                            .{RtcSession/peerToken}
                .{then}
                    {continue}
                {if}
                    @session
                    .{=}
                        @record
                        .{Rtc/currentRtcSession}
                .{then}
                    {continue}
                {Record/update}
                    [0]
                        @session
                    [1]
                        [RtcSession/connectionState]
                            Not connected: sending initial RTC offer
                {Rtc/_addLogEntry}
                    [0]
                        @record
                    [1]
                        @session
                        .{RtcSession/peerToken}
                    [2]
                        init call
                    [3]
                        [step]
                            init call
                {Rtc/_callPeer}
                    [0]
                        @record
                    [1]
                        @session
                        .{RtcSession/peerToken}
`;
