/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            RtcInvitationCardComponent
        [Model/fields]
            thread
        [Model/template]
            root
                partnerInfo
                    partnerInfoImage
                    partnerInfoName
                    partnerInfoText
                buttonList
                    refuse
                        refuseIcon
                    accept
                        acceptIcon
`;
