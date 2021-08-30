/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            unmute
        [Field/model]
            SoundEffects
        [Field/type]
            one
        [Field/target]
            SoundEffect
        [Field/isCausal]
            true
        [Field/default]
            {Record/insert}
                [Record/models]
                    SoundEffect
                [SoundEffect/defaultVolume]
                    0.2
                [SoundEffect/filename]
                    unmute_1
`;
