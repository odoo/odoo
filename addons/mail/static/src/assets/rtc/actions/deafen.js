/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/deafen
        [Action/behavior]
            {Rtc/setDeafState}
                true
            {SoundEffect/play}
                {SoundEffects/deafen}
`;
