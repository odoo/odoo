/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            RtcController
        [Model/fields]
            callViewer
            isSmall
            rtcOptionList
        [Model/id]
            RtcController/callViewer
        [Model/actions]
            RtcController/onClickCamera
            RtcController/onClickDeafen
            RtcController/onClickMicrophone
            RtcController/onClickRejectCall
            RtcController/onClickScreen
            RtcController/onClickToggleAudioCall
            RtcController/onClickToggleVideoCall
`;
