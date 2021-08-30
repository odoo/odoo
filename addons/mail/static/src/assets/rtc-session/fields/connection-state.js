/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        State of the connection with this session, uses RTCPeerConnection.iceConnectionState
        once a peerConnection has been initialized.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            connectionState
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            String
        [Field/default]
            {Locale/text}
                Waiting for the peer to send a RTC offer
`;
