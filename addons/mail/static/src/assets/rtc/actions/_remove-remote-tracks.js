/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Terminates the Transceivers of the peer connection.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_removeRemoteTracks
        [Action/params]
            peerConnection
                [type]
                    RTCPeerConnection
            record
                [type]
                    Rtc
        [Action/behavior]
            :RTCRtpSenders
                {RTCPeerConnection/getSenders}
                    @peerConnection
            {foreach}
                @RTCRtpSenders
            .{as}
                sender
            .{do}
                {try}
                    {RTCPeerConnection/removeTrack}
                        [0]
                            @peerConnection
                        [1]
                            @sender
                .{catch}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            error
                        [Function/out]
                            {Dev/comment}
                                ignore error
            {foreach}
                {RTCPeerConnection/getTransceivers}
                    @peerConnection
            .{as}
                transceiver
            .{do}
                {try}
                    {Transceiver/stop}
                        @transceiver
                .{catch}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            error
                        [Function/out]
                            {Dev/comment}
                                transceiver may already be stopped by the remote.
`;
