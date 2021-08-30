/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            RtcSession
        [Model/fields]
            _timeoutId
            audioElement
            audioStream
            avatarUrl
            calledChannels
            channel
            connectionState
            guest
            id
            isAudioInError
            isCameraOn
            isDeaf
            isMute
            isOwnSession
            isSelfMuted
            isScreenSharingOn
            isTalking
            name
            partner
            peerToken
            rtc
            videoStream
            volume
        [Model/id]
            RtcSession/id
        [Model/actions]
            RtcSession/_debounce
            RtcSession/_removeAudio
            RtcSession/removeVideo
            RtcSession/reset
            RtcSession/setAudio
            RtcSession/setVolume
            RtcSession/toggleDeaf
            RtcSession/updateAndBroadcast
        [Model/lifecycles]
            onWillDelete
`;
