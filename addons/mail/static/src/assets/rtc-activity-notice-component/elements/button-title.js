/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonTitle
        [Element/model]
            RtcActivityNoticeComponent
        [web.Element/tag]
            em
        [web.Element/class]
            tex-truncate
        [web.Element/textContent]
            {Rtc/channel}
            .{Thread/displayName}
`;
