/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The default volume to play this sound effect, when unspecified.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            defaultVolume
        [Field/model]
            SoundEffect
        [Field/type]
            attr
        [Field/target]
            Float
        [Field/default]
            1
`;
