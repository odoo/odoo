/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            soundEffects
        [Field/model]
            Env
        [Field/type]
            one
        [Field/target]
            SoundEffects
        [Field/isCausal]
            true
        [Field/isReadonly]
            true
        [Field/default]
            {Record/insert}
                [Record/models]
                    SoundEffects
`;
