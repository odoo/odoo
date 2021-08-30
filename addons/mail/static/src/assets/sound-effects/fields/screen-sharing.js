/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            screenSharing
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
                    0.5
                [SoundEffect/filename]
                    share_02
`;
