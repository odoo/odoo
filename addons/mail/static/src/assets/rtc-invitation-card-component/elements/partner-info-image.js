/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            partnerInfoImage
        [Element/model]
            RtcInvitationCardComponent
        [web.Element/tag]
            image
        [web.Element/class]
            rounded-circle
        [web.Element/src]
            @record
            .{RtcInvitationCardComponent/thread}
            .{Thread/rtcInvitingSession}
            .{RtcSession/avatarUrl}
        [Element/onClick]
            {Thread/open}
                @record
                .{RtcInvitationCardComponent/thread}
        [web.Element/alt]
            {Locale/text}
                Avatar
        [web.Element/style]
            [web.scss/margin-bottom]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/width]
                70%
            [web.scss/height]
                70%
            [web.scss/border]
                3px
                solid
                gray
            [web.scss/cursor]
                pointer
`;
