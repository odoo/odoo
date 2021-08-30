/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MediaPreview
        [Model/fields]
            audioRef
            audioStream
            doesBrowserSupportMediaDevices
            isMicrophoneEnabled
            isVideoEnabled
            videoRef
            videoStream
            welcomeView
        [Model/id]
            MediaPreview/welcomeView
        [Model/actions]
            MediaPreview/disableMicrophone
            MediaPreview/disableVideo
            MediaPreview/enableMicrophone
            MediaPreview/enableVideo
            MediaPreview/onClickDisableMicrophoneButton
            MediaPreview/onClickDisableVideoButton
            MediaPreview/onClickEnableMicrophoneButton
            MediaPreview/onClickEnableVideoButton
            MediaPreview/stopTracksOnMediaStream
`;
