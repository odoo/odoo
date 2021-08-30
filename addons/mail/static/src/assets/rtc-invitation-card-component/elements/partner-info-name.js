/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            partnerInfoName
        [Element/model]
            RtcInvitationCardComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            @record
            .{RtcInvitationCardComponent/thread}
            .{Thread/rtcInvitingSession}
            .{RtcSession/name}
        [web.Element/style]
            [web.scss/overflow]
                hidden
            [web.scss/width]
                100%
            [web.scss/font-weight]
                bold
            {scss/include}
                {scss/text-truncate}
            [web.scss/text-align]
                center
`;
