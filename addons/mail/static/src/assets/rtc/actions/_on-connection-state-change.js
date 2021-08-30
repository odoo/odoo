/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_onConnectionStateChange
        [Action/params]
            state
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
                    connection state changed: 
                    .{+}
                        @state
            {switch}
                @state
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
                            [delay]
                                @record
                                .{Rtc/recoveryDelay}
                            [reason]
                                connection 
                                .{+}
                                    @state
                [disconnected]
                    {Rtc/_recoverConnection}
                        [0]
                            @record
                        [1]
                            [delay]
                                @record
                                .{Rtc/recoveryDelay}
                            [reason]
                                connection 
                                .{+}
                                    @state
`;
