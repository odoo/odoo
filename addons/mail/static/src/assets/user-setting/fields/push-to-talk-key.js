/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Formatted string that represent the push to talk key with its modifiers.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            pushToTalkKey
        [Field/model]
            UserSetting
        [Field/type]
            attr
        [Field/target]
            String
`;
