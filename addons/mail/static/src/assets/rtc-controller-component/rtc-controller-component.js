/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            RtcControllerComponent
        [Model/fields]
            rtcController
        [Model/template]
            root
                buttons
                    micButton
                        micButtonIconWrapper
                            micButtonIcon
                    headphoneButton
                        headphoneButtonIconWrapper
                            headphoneButtonIcon
                    cameraButton
                        cameraButtonIconWrapper
                            cameraButtonIcon
                    screenButton
                        screenButtonIconWrapper
                            screenButtonIcon
                    moreButton
                        moreButtonIconWrapper
                            moreButtonIcon
                    moreButtonPopover
                        rtcOptionList
                    joinCallButton
                        joinCallButtonIconWrapper
                            joinCallButtonIcon
                    rejectCallButton
                        rejectCallButtonIconWrapper
                            rejectCallButtonIcon
                    toggleCallButton
                        toggleCallButtonIconWrapper
                            toggleCallButtonIcon
`;
