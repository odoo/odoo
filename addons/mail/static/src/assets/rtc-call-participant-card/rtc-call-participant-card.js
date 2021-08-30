/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            RtcCallParticipantCard
        [Model/fields]
            avatarUrl
            channel
            invitedGuest
            invitedPartner
            isInvitation
            isMinimized
            isTalking
            name
            relationalId
            rtcCallViewerOfMainCard
            rtcCallViewerOfTile
            rtcSession
        [Model/id]
            RtcCallParticipantCard/relationalId
        [Model/actions]
            RtcCallParticipantCard/onChangeVolume
            RtcCallParticipantCard/onClick
            RtcCallParticipantCard/onClickVolumeAnchor
`;
