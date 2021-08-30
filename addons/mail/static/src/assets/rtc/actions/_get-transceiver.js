/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_getTransceiver
        [Action/params]
            peerConnection
                [type]
                    RTCPeerConnection
            trackKind
                [type]
                    String
            record
                [type]
                    Rtc
        [Action/returns]
            RTCRtpTransceiver
                [description]
                    the transceiver used for this trackKind.
        [Action/behavior]
            :transceivers
                {RTCPeerConnection/getTransceivers}
                    @peerConnection
            @transceivers
            .{Collection/at}
                @record
                .{Rtc/transceiverOrder}
                .{Collection/indexOf}
                    @trackKind
`;
