/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/unmute
        [Action/behavior]
            {if}
                {Rtc/audioTrack}
            .{then}
                {Rtc/_setMuteState}
                    false
            .{else}
                {Dev/comment}
                    if we don't have an audioTrack, we try to request it again
                {Rtc/updateLocalAudioTrack}
                    true
            {SoundEffect/play}
                {SoundEffects/unmute}
`;
