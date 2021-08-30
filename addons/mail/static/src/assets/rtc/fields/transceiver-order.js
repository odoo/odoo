/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The order in which transceivers are added, relevant for RTCPeerConnection.getTransceivers which returns
        transceivers in insertion order as per webRTC specifications.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            transceiverOrder
        [Field/model]
            Rtc
        [Field/type]
            attr
        [Field/target]
            Collection<String>
        [Field/default]
            audio
            video
`;
