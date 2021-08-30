/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            RtcOptionList
        [Model/fields]
            component
            rtcController
        [Model/id]
            RtcOptionList/rtcController
        [Model/actions]
            RtcOptionList/onClickActivateFullScreen
            RtcOptionList/onClickDeactivateFullScreen
            RtcOptionList/onClickDownloadLogs
            RtcOptionList/onClickLayout
            RtcOptionList/onClickOptions
`;
