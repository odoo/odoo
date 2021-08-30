/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            refuseIcon
        [Element/model]
            RtcInvitationCardComponent
        [Record/models]
            RtcInvitationCardComponent/buttonIcon
        [web.Element/class]
            fa-times
`;
