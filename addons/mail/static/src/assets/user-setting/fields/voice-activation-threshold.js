/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Normalized volume at which the voice activation system must consider the user as "talking".
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            voiceActivationThreshold
        [Field/model]
            UserSetting
        [Field/type]
            attr
        [Field/target]
            Float
        [Field/default]
            0.05
`;
