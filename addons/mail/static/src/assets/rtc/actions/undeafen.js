/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/undeafen
        [Action/behavior]
            {Rtc/_setDeafState}
                false
            {SoundEffect/play}
                {SoundEffects/undeafen}
`;
