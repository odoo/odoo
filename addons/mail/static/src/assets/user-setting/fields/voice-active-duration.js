/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        how long the voice remains active after releasing the push-to-talk key in ms
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            voiceActiveDuration
        [Field/model]
            UserSetting
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/default]
            0
`;
