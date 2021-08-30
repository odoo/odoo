/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            rtcInvitations
        [Element/model]
            RtcActivityNoticeComponent
        [Field/target]
            RtcInvitationsComponent
`;
