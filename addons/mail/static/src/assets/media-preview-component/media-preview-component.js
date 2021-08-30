/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MediaPreviewComponent
        [Model/fields]
            mediaPreview
        [Model/template]
            root
                videoDisplay
                mediaDevicesStatusCameraOff
                mediaDevicesStatusUnsupported
                buttonsContainer
                    enableMicrophoneButton
                    disableMicrophoneButton
                    enableVideoButton
                    disableVideoButton
                audioPlayer
`;
