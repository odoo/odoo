/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/mute
        [Action/behavior]
            {Rtc/setMuteState}
                true
            {SoundEffect/play}
                {SoundEffects/mute}
`;
