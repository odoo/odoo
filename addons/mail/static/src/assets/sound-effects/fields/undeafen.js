/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            undeafen
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
                    0.15
                [SoundEffect/filename]
                    undeafen_new_01
`;
