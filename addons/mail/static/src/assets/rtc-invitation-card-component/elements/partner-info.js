/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            partnerInfo
        [Element/model]
            RtcInvitationCardComponent
        [Element/isPresent]
            @record
            .{RtcInvitationCardComponent/thread}
            .{Thread/rtcInvitingSession}
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/width]
                130
                px
            [web.scss/flex-direction]
                column
            [web.scss/justify-content]
                space-around
            [web.scss/align-items]
                center
            [web.scss/white-space]
                nowrap
`;
