/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_onICEConnectionStateChange
        [Action/params]
            connectionSstate
                [type]
                    String
                [description]
                    the new state of the connection
            token
                [type]
                    String
                [description]
                    of the peer whose the connection changed
            record
                [type]
                    Rtc
        [Action/behavior]
            {Rtc/_addLogEntry}
                [0]
                    @record
                [1]
                    @token
                [2]
                    ICE connection state changed: 
                    .{+}
                        @connectionState
                [3]
                    [state]
                        @connectionState
            :rtcSession
                {Record/findById}
                    [RtcSession/id]
                        @token
            {if}
                @rtcSession
                .{isFalsy}
            .{then}
                {break}
            {Record/update}
                [0]
                    @rtcSession
                [1]
                    [RtcSession/connectionState]
                        @connectionState
            {switch}
                @connectionState
            .{case}
                [closed]
                    {Rtc/_removePeer}
                        [0]
                            @record
                        [1]
                            @token
                [failed]
                    {Rtc/_recoverConnection}
                        [0]
                            @record
                        [1]
                            @token
                        [2]
                            [delay]
                                @record
                                .{Rtc/recoveryDelay}
                            [reason]
                                ice connection 
                                .{+}
                                    @connectionState
                [disconnected]
                    {Rtc/_recoverConnection}
                        [0]
                            @record
                        [1]
                            @token
                        [2]
                            [delay]
                                @record
                                .{Rtc/recoveryDelay}
                            [reason]
                                ice connection 
                                .{+}
                                    @connectionState
`;
