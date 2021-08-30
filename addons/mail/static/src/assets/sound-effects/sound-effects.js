/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            SoundEffects
        [Model/fields]
            channelJoin
            channelLeave
            deafen
            incomingCall
            memberLeave
            mute
            newMessage
            pushToTalkOn
            pushToTalkOff
            screenSharing
            undeafen
            unmute
        [Model/id]
            SoundEffects/messaging
`;
