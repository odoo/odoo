/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Removes and disconnects all the peerConnections that are not current members
        of the call.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/filterCallees
        [Action/params]
            currentSessions
                [type]
                    Collection<RtcSession>
                [description]
                    list of sessions of this call.
            record
                [type]
                    Rtc
        [Action/behavior]
            :currentSessionsTokens
                {Record/insert}
                    [Record/models]
                        Set
                    @currentSessions
                    .{Collection/map}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                item
                            [Function/out]
                                @item
                                .{RtcSession/peerToken}
            {foreach}
                @record
                .{Rtc/_peerConnections}
            .{as}
                token
            .{do}
                {if}
                    {Set/has}
                        [0]
                            @currentSessionsTokens
                        [1]
                            @token
                    .{isFalsy}
                .{then}
                    {Rtc/_addLogEntry}
                        [0]
                            @record
                        [1]
                            @token
                        [2]
                            session removed from the server
                    {Rtc/_removePeer}
                        [0]
                            @rtc
                        [1]
                            @token
            {if}
                @record
                .{Rtc/channel}
                .{&}
                    @record
                    .{Rtc/currentRtcSession}
                .{&}
                    {Set/has}
                        [0]
                            @currentSessionsTokens
                        [1]
                            @record
                            .{Rtc/currentRtcSession}
                            .{RtcSession/peerToken}
                    .{isFalsy}
            .{then}
                {Dev/comment}
                    if the current RTC session is not in the channel sessions,
                    this call is no longer valid.
                {Thread/endCall}
                    @record
                    .{Rtc/channel}
`;
