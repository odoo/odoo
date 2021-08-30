/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        true if the browser supports webRTC
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isClientRtcCompatible
        [Field/model]
            Rtc
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            true
        [Field/compute]
            {web.Browser/RTCPeerConnection}
            .{&}
                {web.Browser/MediaStream}
`;
