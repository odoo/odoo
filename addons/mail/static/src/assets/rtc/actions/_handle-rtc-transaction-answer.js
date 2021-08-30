/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_handleRtcTransactionAnswer
        [Action/params]
            fromToken
                [type]
                    String
            sdp
                [type]
                    Object
                [description]
                    Session Description Protocol
            record
                [type]
                    Rtc
        [Action/behavior]
            :peerConnection
                @record
                .{Rtc/_peerConnections}
                .{Dict/get}
                    @fromToken
            {if}
                @peerConnection
                .{isFalsy}
                .{|}
                    {Set/has}
                        [0]
                            @record
                            .{Rtc/invalidIceConnectionStates}
                        [1]
                            @peerConnection
                            .{RTCPeerConnection/connectionState}
                .{|}
                    @peerConnection
                    .{RTCPeerConnection/signalingState}
                    .{=}
                        stable
            .{then}
                {break}
            {if}
                @peerConnection
                .{RTCPeerConnection/signalingState}
                .{=}
                    have-remote-offer
                .{then}
                    {Dev/comment}
                        we already have an offer
                    {break}
            :rtcSessionDescription
                {Record/insert}
                    [Record/models]
                        RTCSessionDescription
                    @sdp
            {try}
                {RtcPeerConnection/setRemoteDescription}
                    [0]
                        @peerConnection
                    [1]
                        @rtcSessionDescription
            .{catch}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        error
                    [Function/out]
                        {Rtc/_addLogEntry}
                            [0]
                                @record
                            [1]
                                @fromToken
                            [2]
                                answer handling: Failed at setting remote Description
                            [3]
                                [error]
                                    @error
                        {Dev/comment}
                            ignored the transaction may have been resolved by
                            another concurrent offer.
`;
