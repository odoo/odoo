/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns a string representation of a data channel for logging and
        debugging purposes.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_serializeRTCDataChannel
        [Action/params]
            dataChannel
                [type]
                    RTCDataChannel
            record
                [type]
                    Rtc
        [Action/returns]
            String
        [Action/behavior]
            {JSON/stringify}
                {Object/fromEntries}
                    {Record/insert}
                        [Record/models]
                            Collection
                        binaryType
                        bufferedAmount
                        bufferedAmountLowThreshold
                        id
                        label
                        maxPacketLifeTime
                        maxRetransmits
                        negotiated
                        ordered
                        protocol
                        readyState
                    .{Collection/map}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                p
                            [Function/out]
                                {Record/insert}
                                    [Record/models]
                                        Collection
                                    [0]
                                        @p
                                    [1]
                                        @dataChannel
                                        .{Dict/get}
                                            @p
`;
