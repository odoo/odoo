/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            RtcActivityNoticeComponent
        [Model/template]
            root
                rtcInvitations
                button
                    buttonContent
                        outputIndicator
                        buttonTitle
        [Model/action]
            RtcActivityNoticeComponent/_onClick
`;
