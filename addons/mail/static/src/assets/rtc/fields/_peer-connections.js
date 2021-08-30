/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Object { token: peerConnection<RTCPeerConnection> }
        Contains the RTCPeerConnection established with the other rtc sessions.
        Exposing this field and keeping references to closed peer connections may lead
        to difficulties reconnecting to the same peer.

        garbage collection of peerConnections is important for peerConnection.close().
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _peerConnections
        [Field/model]
            Rtc
        [Field/type]
            attr
        [Field/target]
            Dict
        [Field/default]
            {Record/insert}
                [Record/models]
                    Dict
`;
