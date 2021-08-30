/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        ICE servers used by RTCPeerConnection to retrieve the public IP address (STUN)
        or to relay packets when necessary (TURN).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            iceServers
        [Field/model]
            Rtc
        [Field/type]
            attr
        [Field/target]
            Collection<IceServer>
        [Field/default]
            {Record/insert}
                [Record/models]
                    IceServer
                [IceServer/urls]
                    [0]
                        stun:stun1.l.google.com:19302
                    [1]
                        stun:stun2.l.google.com:19302
`;
