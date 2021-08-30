/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            RtcInvitationsComponent
        [Model/template]
            root
                rtcInvitationCardForeach
`;
