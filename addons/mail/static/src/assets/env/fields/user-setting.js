/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            userSetting
        [Field/model]
            Env
        [Field/type]
            one
        [Field/target]
            UserSetting
        [Field/isCausal]
            true
`;
