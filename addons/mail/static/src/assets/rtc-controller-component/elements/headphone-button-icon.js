/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            headphoneButtonIcon
        [Element/model]
            RtcControllerComponent
        [Record/models]
            RtcControllerComponent/buttonIcon
        [web.Element/class]
            {if}
                {Rtc/currentRtcSession}
                .{RtcSession/isDeaf}
            .{then}
                fa-deaf
            .{else}
                fa-headphones
`;
